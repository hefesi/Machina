"""Dynamic fragment memory with non-destructive priority decay.

Fragments remain in persistent storage even when their active priority falls.
The active view is a bounded projection over the archive, not a deletion policy.
This module is a deterministic memory substrate, not a semantic reasoner.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3
from typing import Any, Mapping
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number between 0 and 1")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite number between 0 and 1") from error
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be a finite number between 0 and 1")
    return result


def _json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError("value must be finite JSON data") from error


@dataclass(frozen=True, slots=True)
class MemoryFragment:
    id: str
    content: str
    kind: str
    source_uri: str
    importance: float
    confidence: float
    priority: float
    access_count: int
    created_at: str
    last_accessed_at: str
    pinned: bool
    tags: tuple[str, ...]
    related_ids: tuple[str, ...]
    metadata: Mapping[str, Any]


class FragmentMemory:
    """SQLite archive with a priority-ranked active view and associative links.

    Priority combines stable importance, confidence, usage reinforcement, and
    exponential recency decay. A fragment's source record is never removed by
    prioritization. Pinning protects high-value items from active-view pruning,
    but does not bypass an explicit result limit.
    """

    schema_version = 1

    def __init__(
        self,
        storage_path: str | Path,
        *,
        decay_per_day: float = 0.04,
        usage_reinforcement: float = 0.08,
    ) -> None:
        self.decay_per_day = _score(decay_per_day, "decay_per_day")
        self.usage_reinforcement = _score(usage_reinforcement, "usage_reinforcement")
        path = str(storage_path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA busy_timeout = 5000")
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_feedback_batches (
                operation_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_fragments (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                kind TEXT NOT NULL,
                source_uri TEXT NOT NULL,
                importance REAL NOT NULL CHECK (importance BETWEEN 0 AND 1),
                confidence REAL NOT NULL CHECK (confidence BETWEEN 0 AND 1),
                access_count INTEGER NOT NULL DEFAULT 0 CHECK (access_count >= 0),
                created_at TEXT NOT NULL,
                last_accessed_at TEXT NOT NULL,
                pinned INTEGER NOT NULL DEFAULT 0 CHECK (pinned IN (0, 1)),
                tags_json TEXT NOT NULL,
                related_ids_json TEXT NOT NULL,
                metadata_json TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_context_importance (
                fragment_id TEXT NOT NULL,
                context_key TEXT NOT NULL,
                score REAL NOT NULL CHECK (score BETWEEN 0 AND 1),
                updated_at TEXT NOT NULL,
                PRIMARY KEY (fragment_id, context_key),
                FOREIGN KEY (fragment_id) REFERENCES memory_fragments(id) ON DELETE CASCADE
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_context_feedback_batches (
                operation_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self._db.commit()
        self._closed = False

    def close(self) -> None:
        if not self._closed:
            self._db.close()
            self._closed = True

    def __enter__(self) -> "FragmentMemory":
        self._ensure_open()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def add(
        self,
        content: str,
        *,
        kind: str = "fact",
        source_uri: str,
        importance: float = 0.5,
        confidence: float = 0.5,
        tags: tuple[str, ...] | list[str] = (),
        related_ids: tuple[str, ...] | list[str] = (),
        metadata: Mapping[str, Any] | None = None,
        pinned: bool = False,
        fragment_id: str | None = None,
    ) -> MemoryFragment:
        self._ensure_open()
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be a non-empty string")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("kind must be a non-empty string")
        if not isinstance(source_uri, str) or not source_uri.strip():
            raise ValueError("source_uri must identify the origin of the fragment")
        if not isinstance(pinned, bool):
            raise ValueError("pinned must be boolean")
        importance_value = _score(importance, "importance")
        confidence_value = _score(confidence, "confidence")
        if not all(isinstance(tag, str) and tag.strip() for tag in tags):
            raise ValueError("tags must contain non-empty strings")
        if not all(isinstance(item, str) and item.strip() for item in related_ids):
            raise ValueError("related_ids must contain non-empty strings")
        identifier = fragment_id or f"fragment_{uuid4().hex}"
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("fragment_id must be a non-empty string")
        created = _now()
        self._db.execute(
            """INSERT INTO memory_fragments
            (id, content, kind, source_uri, importance, confidence, access_count,
             created_at, last_accessed_at, pinned, tags_json, related_ids_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)""",
            (identifier, content.strip(), kind.strip(), source_uri.strip(),
             importance_value, confidence_value, created, created, int(pinned),
             _json(list(dict.fromkeys(tags))), _json(list(dict.fromkeys(related_ids))),
             _json(dict(metadata or {}))),
        )
        self._db.commit()
        return self.get(identifier, record_access=False)

    def get(self, fragment_id: str, *, record_access: bool = True) -> MemoryFragment:
        self._ensure_open()
        row = self._db.execute(
            "SELECT * FROM memory_fragments WHERE id = ?", (fragment_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown memory fragment: {fragment_id}")
        if record_access:
            self._db.execute(
                "UPDATE memory_fragments SET access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
                (_now(), fragment_id),
            )
            self._db.commit()
            row = self._db.execute(
                "SELECT * FROM memory_fragments WHERE id = ?", (fragment_id,)
            ).fetchone()
        return self._from_row(row)

    def apply_importance_feedback_batch(
        self,
        deltas: Mapping[str, float],
        *,
        operation_id: str,
    ) -> tuple[dict[str, MemoryFragment], dict[str, dict[str, float]], bool]:
        """Apply an idempotent batch of importance deltas in one SQLite transaction.

        Reusing an operation ID with the same payload returns the original
        before/after audit values without applying the deltas a second time.
        Reusing it with different input is rejected. This supports safe retries
        when a caller also records the outcome in a separate event journal.
        """
        self._ensure_open()
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        if not isinstance(deltas, Mapping) or not deltas:
            raise ValueError("deltas must be a non-empty mapping")

        normalized: dict[str, float] = {}
        for fragment_id, delta in deltas.items():
            if not isinstance(fragment_id, str) or not fragment_id.strip():
                raise ValueError("fragment IDs must be non-empty strings")
            if isinstance(delta, bool) or not isinstance(delta, (int, float)) or not math.isfinite(delta):
                raise ValueError("each importance delta must be finite")
            normalized[fragment_id] = float(delta)
        payload_json = _json(normalized)

        self._db.execute("BEGIN IMMEDIATE")
        try:
            prior = self._db.execute(
                "SELECT payload_json, result_json FROM memory_feedback_batches WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if prior is not None:
                if prior["payload_json"] != payload_json:
                    raise ValueError("operation_id was already used with different feedback")
                results = json.loads(prior["result_json"])
                fragments: dict[str, MemoryFragment] = {}
                for fragment_id in normalized:
                    row = self._db.execute(
                        "SELECT * FROM memory_fragments WHERE id = ?", (fragment_id,)
                    ).fetchone()
                    if row is None:
                        raise KeyError(fragment_id)
                    fragments[fragment_id] = self._from_row(row)
                self._db.commit()
                return fragments, results, False

            before_after: dict[str, dict[str, float]] = {}
            now = _now()
            for fragment_id, delta in normalized.items():
                row = self._db.execute(
                    "SELECT importance, pinned FROM memory_fragments WHERE id = ?", (fragment_id,)
                ).fetchone()
                if row is None:
                    raise KeyError(fragment_id)
                before = float(row["importance"])
                # Pinning protects retention and active-view priority, not
                # task relevance. Importance can still adapt while the pinned
                # fragment remains protected from active-view pruning.
                after = min(1.0, max(0.0, before + delta))
                before_after[fragment_id] = {"before": before, "after": after}
            for fragment_id, values in before_after.items():
                self._db.execute(
                    "UPDATE memory_fragments SET importance = ?, access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
                    (values["after"], now, fragment_id),
                )
            self._db.execute(
                "INSERT INTO memory_feedback_batches (operation_id, payload_json, result_json, created_at) VALUES (?, ?, ?, ?)",
                (operation_id, payload_json, _json(before_after), now),
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        fragments = {}
        for fragment_id in normalized:
            row = self._db.execute(
                "SELECT * FROM memory_fragments WHERE id = ?", (fragment_id,)
            ).fetchone()
            if row is None:
                raise KeyError(fragment_id)
            fragments[fragment_id] = self._from_row(row)
        return fragments, before_after, True

    def reinforce(
        self,
        fragment_id: str,
        *,
        importance_delta: float = 0.0,
        confidence: float | None = None,
        pin: bool | None = None,
    ) -> MemoryFragment:
        """Explicitly reinforce a fragment; values are clamped only by validation."""
        self._ensure_open()
        fragment = self.get(fragment_id, record_access=False)
        if isinstance(importance_delta, bool) or not isinstance(importance_delta, (int, float)) or not math.isfinite(importance_delta):
            raise ValueError("importance_delta must be finite")
        importance = min(1.0, max(0.0, fragment.importance + float(importance_delta)))
        new_confidence = fragment.confidence if confidence is None else _score(confidence, "confidence")
        if pin is not None and not isinstance(pin, bool):
            raise ValueError("pin must be boolean or None")
        pinned = fragment.pinned if pin is None else pin
        self._db.execute(
            "UPDATE memory_fragments SET importance = ?, confidence = ?, pinned = ?, access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
            (importance, new_confidence, int(pinned), _now(), fragment_id),
        )
        self._db.commit()
        return self.get(fragment_id, record_access=False)

    def link(self, fragment_id: str, related_id: str) -> MemoryFragment:
        """Create a bidirectional association without merging or deleting fragments."""
        first = self.get(fragment_id, record_access=False)
        second = self.get(related_id, record_access=False)
        if first.id == second.id:
            raise ValueError("a fragment cannot be linked to itself")
        self._set_related(first, second.id)
        self._set_related(second, first.id)
        self._db.commit()
        return self.get(fragment_id, record_access=False)

    def active(self, *, limit: int = 20, query_tags: tuple[str, ...] | list[str] = ()) -> list[MemoryFragment]:
        """Return a bounded active view; archived fragments remain untouched."""
        self._ensure_open()
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if not all(isinstance(tag, str) and tag.strip() for tag in query_tags):
            raise ValueError("query_tags must contain non-empty strings")
        requested = {tag.casefold() for tag in query_tags}
        rows = self._db.execute("SELECT * FROM memory_fragments").fetchall()
        ranked: list[tuple[float, MemoryFragment]] = []
        now = datetime.now(timezone.utc)
        for row in rows:
            fragment = self._from_row(row)
            age_days = max(0.0, (now - datetime.fromisoformat(fragment.last_accessed_at)).total_seconds() / 86400)
            decay = math.exp(-self.decay_per_day * age_days)
            usage = min(1.0, math.log1p(fragment.access_count) / 5.0) * self.usage_reinforcement
            tag_bonus = 0.2 if requested and requested.intersection(tag.casefold() for tag in fragment.tags) else 0.0
            score = min(1.0, fragment.importance * decay + usage + tag_bonus)
            if fragment.pinned:
                score = 1.0
            ranked.append((score, fragment))
        ranked.sort(key=lambda pair: (-pair[0], -pair[1].importance, pair[1].id))
        return [self._with_priority(fragment, score) for score, fragment in ranked[:limit]]

    def archive(self, *, limit: int | None = None) -> list[MemoryFragment]:
        """List stored fragments regardless of active priority, oldest first."""
        self._ensure_open()
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            raise ValueError("limit must be a positive integer or None")
        sql = "SELECT * FROM memory_fragments ORDER BY created_at, id"
        if limit is not None:
            sql += " LIMIT ?"
            rows = self._db.execute(sql, (limit,)).fetchall()
        else:
            rows = self._db.execute(sql).fetchall()
        return [self._from_row(row) for row in rows]

    def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        include_related: bool = True,
        context: str | None = None,
    ) -> list[MemoryFragment]:
        """Retrieve fragments by lexical overlap and optionally one-hop associations.

        This is an explainable lexical baseline, not semantic understanding. A
        related fragment may be returned as context even when its own wording
        does not overlap the query. An optional explicit context applies a
        separate task-relative score without changing global importance.
        Retrieval never deletes or rewrites memory.
        """
        self._ensure_open()
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        import re

        def tokens(text: str) -> set[str]:
            return {token.casefold() for token in re.findall(r"\w+", text, flags=re.UNICODE) if len(token) > 1}

        if context is not None and (not isinstance(context, str) or not context.strip()):
            raise ValueError("context must be a non-empty string when provided")
        context_key = context.strip().casefold() if context is not None else None
        query_tokens = tokens(query)
        if not query_tokens:
            return []
        rows = self._db.execute("SELECT * FROM memory_fragments").fetchall()
        context_scores: dict[str, float] = {}
        if context_key is not None:
            context_scores = {
                str(row["fragment_id"]): float(row["score"])
                for row in self._db.execute(
                    "SELECT fragment_id, score FROM memory_context_importance WHERE context_key = ?",
                    (context_key,),
                ).fetchall()
            }
        fragments = {str(row["id"]): self._from_row(row) for row in rows}
        ranked: list[tuple[float, str]] = []
        direct_matches: set[str] = set()
        for fragment in fragments.values():
            searchable = " ".join((fragment.content, fragment.kind, " ".join(fragment.tags), _json(fragment.metadata)))
            overlap = len(query_tokens & tokens(searchable)) / len(query_tokens)
            if overlap > 0:
                direct_matches.add(fragment.id)
                tag_overlap = bool(query_tokens & tokens(" ".join(fragment.tags)))
                score = 0.70 * overlap + 0.15 * fragment.importance + 0.10 * fragment.confidence
                score += 0.05 if tag_overlap else 0.0
                if context_key is not None:
                    # Context is a bounded tie-breaker/adjustment, not a replacement
                    # for lexical evidence or the fragment's global importance.
                    score += 0.15 * (context_scores.get(fragment.id, 0.5) - 0.5)
                ranked.append((score, fragment.id))
        if include_related and direct_matches:
            related_ids = {
                related_id
                for fragment_id in direct_matches
                for related_id in fragments[fragment_id].related_ids
                if related_id in fragments and related_id not in direct_matches
            }
            for related_id in related_ids:
                fragment = fragments[related_id]
                score = 0.20 + 0.10 * fragment.importance + 0.05 * fragment.confidence
                if context_key is not None:
                    score += 0.15 * (context_scores.get(fragment.id, 0.5) - 0.5)
                ranked.append((score, related_id))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [fragments[fragment_id] for _, fragment_id in ranked[:limit]]

    def apply_context_feedback_batch(
        self,
        outcomes: Mapping[str, bool],
        *,
        context: str,
        operation_id: str,
        strength: float = 0.10,
    ) -> tuple[dict[str, float], bool]:
        """Update task-relative retrieval scores without changing global importance.

        Scores start at 0.5 for an unseen (fragment, context) pair and are
        clamped to [0, 1]. A stable operation ID makes retries idempotent.
        """
        self._ensure_open()
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        context_key = context.strip().casefold()
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        amount = _score(strength, "strength")
        if not isinstance(outcomes, Mapping) or not outcomes:
            raise ValueError("outcomes must be a non-empty mapping")
        normalized: dict[str, bool] = {}
        for fragment_id, useful in outcomes.items():
            if not isinstance(fragment_id, str) or not fragment_id.strip():
                raise ValueError("fragment IDs must be non-empty strings")
            if not isinstance(useful, bool):
                raise ValueError("every usefulness label must be boolean")
            normalized[fragment_id] = useful
        deltas = {
            fragment_id: amount if useful else -amount
            for fragment_id, useful in normalized.items()
        }
        payload_json = _json({"context": context_key, "deltas": deltas})
        self._db.execute("BEGIN IMMEDIATE")
        try:
            prior = self._db.execute(
                "SELECT payload_json, result_json FROM memory_context_feedback_batches WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if prior is not None:
                if prior["payload_json"] != payload_json:
                    raise ValueError("operation_id was already used with different context feedback")
                results = json.loads(prior["result_json"])
                self._db.commit()
                return {key: float(value["after"]) for key, value in results.items()}, False

            results: dict[str, dict[str, float]] = {}
            now = _now()
            for fragment_id, delta in deltas.items():
                exists = self._db.execute(
                    "SELECT 1 FROM memory_fragments WHERE id = ?", (fragment_id,)
                ).fetchone()
                if exists is None:
                    raise KeyError(f"unknown memory fragment: {fragment_id}")
                row = self._db.execute(
                    "SELECT score FROM memory_context_importance WHERE fragment_id = ? AND context_key = ?",
                    (fragment_id, context_key),
                ).fetchone()
                before = float(row["score"]) if row is not None else 0.5
                after = min(1.0, max(0.0, before + delta))
                results[fragment_id] = {"before": before, "after": after}
            for fragment_id, values in results.items():
                self._db.execute(
                    """INSERT INTO memory_context_importance
                    (fragment_id, context_key, score, updated_at) VALUES (?, ?, ?, ?)
                    ON CONFLICT(fragment_id, context_key) DO UPDATE SET
                    score = excluded.score, updated_at = excluded.updated_at""",
                    (fragment_id, context_key, values["after"], now),
                )
            self._db.execute(
                """INSERT INTO memory_context_feedback_batches
                (operation_id, payload_json, result_json, created_at) VALUES (?, ?, ?, ?)""",
                (operation_id, payload_json, _json(results), now),
            )
            self._db.commit()
            return {key: float(value["after"]) for key, value in results.items()}, True
        except Exception:
            self._db.rollback()
            raise

    def context_importance(self, fragment_id: str, context: str) -> float:
        """Return a fragment's task-relative score, or neutral 0.5 if unseen."""
        self._ensure_open()
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        self.get(fragment_id, record_access=False)
        row = self._db.execute(
            "SELECT score FROM memory_context_importance WHERE fragment_id = ? AND context_key = ?",
            (fragment_id, context.strip().casefold()),
        ).fetchone()
        return float(row["score"]) if row is not None else 0.5

    def count(self) -> int:
        self._ensure_open()
        return int(self._db.execute("SELECT COUNT(*) FROM memory_fragments").fetchone()[0])

    def _set_related(self, fragment: MemoryFragment, other_id: str) -> None:
        related = list(fragment.related_ids)
        if other_id not in related:
            related.append(other_id)
        self._db.execute(
            "UPDATE memory_fragments SET related_ids_json = ? WHERE id = ?",
            (_json(related), fragment.id),
        )

    @staticmethod
    def _from_row(row: sqlite3.Row) -> MemoryFragment:
        created = datetime.fromisoformat(str(row["created_at"]))
        last = datetime.fromisoformat(str(row["last_accessed_at"]))
        age_days = max(0.0, (datetime.now(timezone.utc) - last).total_seconds() / 86400)
        # A default display score; active() computes with the configured policy.
        priority = float(row["importance"]) * math.exp(-0.04 * age_days)
        if bool(row["pinned"]):
            priority = 1.0
        return MemoryFragment(
            id=str(row["id"]), content=str(row["content"]), kind=str(row["kind"]),
            source_uri=str(row["source_uri"]), importance=float(row["importance"]),
            confidence=float(row["confidence"]), priority=min(1.0, priority),
            access_count=int(row["access_count"]), created_at=created.isoformat(),
            last_accessed_at=last.isoformat(), pinned=bool(row["pinned"]),
            tags=tuple(json.loads(row["tags_json"])),
            related_ids=tuple(json.loads(row["related_ids_json"])),
            metadata=json.loads(row["metadata_json"]),
        )

    @staticmethod
    def _with_priority(fragment: MemoryFragment, priority: float) -> MemoryFragment:
        from dataclasses import replace
        return replace(fragment, priority=priority)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("fragment memory is closed")
