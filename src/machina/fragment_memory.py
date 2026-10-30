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
        context_decay_half_life_seconds: float | None = None,
        association_decay_half_life_seconds: float | None = None,
    ) -> None:
        self.decay_per_day = _score(decay_per_day, "decay_per_day")
        self.usage_reinforcement = _score(usage_reinforcement, "usage_reinforcement")
        if context_decay_half_life_seconds is not None:
            if (
                isinstance(context_decay_half_life_seconds, bool)
                or not isinstance(context_decay_half_life_seconds, (int, float))
                or not math.isfinite(context_decay_half_life_seconds)
                or context_decay_half_life_seconds <= 0
            ):
                raise ValueError("context_decay_half_life_seconds must be a positive finite number or None")
            context_decay_half_life_seconds = float(context_decay_half_life_seconds)
        self.context_decay_half_life_seconds = context_decay_half_life_seconds
        if association_decay_half_life_seconds is not None:
            if (
                isinstance(association_decay_half_life_seconds, bool)
                or not isinstance(association_decay_half_life_seconds, (int, float))
                or not math.isfinite(association_decay_half_life_seconds)
                or association_decay_half_life_seconds <= 0
            ):
                raise ValueError("association_decay_half_life_seconds must be a positive finite number or None")
            association_decay_half_life_seconds = float(association_decay_half_life_seconds)
        self.association_decay_half_life_seconds = association_decay_half_life_seconds
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
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_context_feedback_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                operation_id TEXT NOT NULL,
                fragment_id TEXT NOT NULL,
                context_key TEXT NOT NULL,
                useful INTEGER NOT NULL CHECK (useful IN (0, 1)),
                before_score REAL NOT NULL CHECK (before_score BETWEEN 0 AND 1),
                after_score REAL NOT NULL CHECK (after_score BETWEEN 0 AND 1),
                created_at TEXT NOT NULL,
                UNIQUE (operation_id, fragment_id),
                FOREIGN KEY (fragment_id) REFERENCES memory_fragments(id) ON DELETE CASCADE
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_association_evidence (
                fragment_a TEXT NOT NULL,
                fragment_b TEXT NOT NULL,
                observations INTEGER NOT NULL CHECK (observations >= 1),
                contexts_json TEXT NOT NULL,
                last_observed_at TEXT NOT NULL,
                PRIMARY KEY (fragment_a, fragment_b),
                CHECK (fragment_a < fragment_b),
                FOREIGN KEY (fragment_a) REFERENCES memory_fragments(id) ON DELETE CASCADE,
                FOREIGN KEY (fragment_b) REFERENCES memory_fragments(id) ON DELETE CASCADE
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_association_context_evidence (
                fragment_a TEXT NOT NULL,
                fragment_b TEXT NOT NULL,
                context_key TEXT NOT NULL,
                observations INTEGER NOT NULL CHECK (observations >= 1),
                last_observed_at TEXT NOT NULL,
                PRIMARY KEY (fragment_a, fragment_b, context_key),
                CHECK (fragment_a < fragment_b),
                FOREIGN KEY (fragment_a, fragment_b)
                    REFERENCES memory_association_evidence(fragment_a, fragment_b)
                    ON DELETE CASCADE
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_association_context_utility (
                fragment_a TEXT NOT NULL,
                fragment_b TEXT NOT NULL,
                context_key TEXT NOT NULL,
                score REAL NOT NULL CHECK (score BETWEEN 0 AND 1),
                updated_at TEXT NOT NULL,
                PRIMARY KEY (fragment_a, fragment_b, context_key),
                CHECK (fragment_a < fragment_b),
                FOREIGN KEY (fragment_a, fragment_b)
                    REFERENCES memory_association_evidence(fragment_a, fragment_b)
                    ON DELETE CASCADE
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_association_feedback_batches (
                operation_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_association_observations (
                operation_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_sequence_transitions (
                previous_fragment_id TEXT NOT NULL,
                next_fragment_id TEXT NOT NULL,
                context_key TEXT NOT NULL,
                observations INTEGER NOT NULL CHECK (observations >= 1),
                last_observed_at TEXT NOT NULL,
                PRIMARY KEY (previous_fragment_id, next_fragment_id, context_key),
                FOREIGN KEY (previous_fragment_id) REFERENCES memory_fragments(id) ON DELETE CASCADE,
                FOREIGN KEY (next_fragment_id) REFERENCES memory_fragments(id) ON DELETE CASCADE
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_sequence_batches (
                operation_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_sequence_context_utility (
                previous_fragment_id TEXT NOT NULL,
                next_fragment_id TEXT NOT NULL,
                context_key TEXT NOT NULL,
                score REAL NOT NULL CHECK (score BETWEEN 0 AND 1),
                updated_at TEXT NOT NULL,
                PRIMARY KEY (previous_fragment_id, next_fragment_id, context_key),
                FOREIGN KEY (previous_fragment_id, next_fragment_id, context_key)
                    REFERENCES memory_sequence_transitions(previous_fragment_id, next_fragment_id, context_key)
                    ON DELETE CASCADE
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_sequence_feedback_batches (
                operation_id TEXT PRIMARY KEY,
                payload_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS memory_fragment_revisions (
                revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
                fragment_id TEXT NOT NULL,
                operation_id TEXT NOT NULL UNIQUE,
                evidence_id TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                prior_content TEXT NOT NULL,
                revised_content TEXT NOT NULL,
                prior_confidence REAL NOT NULL CHECK (prior_confidence BETWEEN 0 AND 1),
                revised_confidence REAL NOT NULL CHECK (revised_confidence BETWEEN 0 AND 1),
                created_at TEXT NOT NULL,
                FOREIGN KEY (fragment_id) REFERENCES memory_fragments(id) ON DELETE CASCADE
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

    def reconsolidate(
        self,
        fragment_id: str,
        *,
        revised_content: str,
        evidence_id: str,
        operation_id: str,
        confidence: float | None = None,
    ) -> tuple[MemoryFragment, dict[str, Any], bool]:
        """Revise a retrieved memory while preserving an append-only prior version.

        The caller supplies new evidence explicitly. Operation IDs make retries
        idempotent; reusing an ID with different input is rejected.
        """
        self._ensure_open()
        for name, value in (("fragment_id", fragment_id), ("evidence_id", evidence_id), ("operation_id", operation_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(revised_content, str) or not revised_content.strip():
            raise ValueError("revised_content must be a non-empty string")
        next_confidence = None if confidence is None else _score(confidence, "confidence")
        payload = _json({
            "fragment_id": fragment_id,
            "revised_content": revised_content,
            "evidence_id": evidence_id,
            "confidence": next_confidence,
        })
        self._db.execute("BEGIN IMMEDIATE")
        try:
            prior_operation = self._db.execute(
                "SELECT fragment_id, evidence_id, payload_json, prior_content, revised_content, "
                "prior_confidence, revised_confidence, created_at FROM memory_fragment_revisions "
                "WHERE operation_id = ?", (operation_id,)
            ).fetchone()
            if prior_operation is not None:
                if (
                    prior_operation["fragment_id"] != fragment_id
                    or prior_operation["evidence_id"] != evidence_id
                    or prior_operation["payload_json"] != payload
                ):
                    raise ValueError("operation_id was already used with different revision data")
                row = self._db.execute("SELECT * FROM memory_fragments WHERE id = ?", (fragment_id,)).fetchone()
                if row is None:
                    raise KeyError(fragment_id)
                revision = dict(prior_operation)
                self._db.commit()
                return self._from_row(row), revision, False

            row = self._db.execute(
                "SELECT content, confidence FROM memory_fragments WHERE id = ?", (fragment_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"unknown memory fragment: {fragment_id}")
            prior_content = str(row["content"])
            prior_confidence = float(row["confidence"])
            revised_confidence = prior_confidence if next_confidence is None else next_confidence
            now = _now()
            self._db.execute(
                "INSERT INTO memory_fragment_revisions "
                "(fragment_id, operation_id, evidence_id, payload_json, prior_content, revised_content, "
                "prior_confidence, revised_confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (fragment_id, operation_id, evidence_id, payload, prior_content, revised_content,
                 prior_confidence, revised_confidence, now),
            )
            self._db.execute(
                "UPDATE memory_fragments SET content = ?, confidence = ?, "
                "access_count = access_count + 1, last_accessed_at = ? WHERE id = ?",
                (revised_content, revised_confidence, now, fragment_id),
            )
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise
        return self.get(fragment_id, record_access=False), {
            "fragment_id": fragment_id,
            "operation_id": operation_id,
            "evidence_id": evidence_id,
            "prior_content": prior_content,
            "revised_content": revised_content,
            "prior_confidence": prior_confidence,
            "revised_confidence": revised_confidence,
            "created_at": now,
        }, True

    def revision_history(self, fragment_id: str) -> list[dict[str, Any]]:
        """Return chronological prior-version records for one fragment."""
        self._ensure_open()
        if not isinstance(fragment_id, str) or not fragment_id.strip():
            raise ValueError("fragment_id must be a non-empty string")
        if self._db.execute(
            "SELECT 1 FROM memory_fragments WHERE id = ?", (fragment_id,)
        ).fetchone() is None:
            raise KeyError(f"unknown memory fragment: {fragment_id}")
        rows = self._db.execute(
            "SELECT fragment_id, operation_id, evidence_id, prior_content, revised_content, "
            "prior_confidence, revised_confidence, created_at FROM memory_fragment_revisions "
            "WHERE fragment_id = ? ORDER BY revision_id", (fragment_id,)
        ).fetchall()
        return [dict(row) for row in rows]

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
        self._link_without_commit(fragment_id, related_id)
        self._db.commit()
        return self.get(fragment_id, record_access=False)

    def _link_without_commit(self, fragment_id: str, related_id: str) -> None:
        first = self.get(fragment_id, record_access=False)
        second = self.get(related_id, record_access=False)
        if first.id == second.id:
            raise ValueError("a fragment cannot be linked to itself")
        self._set_related(first, second.id)
        self._set_related(second, first.id)

    def observe_coactivation(
        self,
        fragment_ids: list[str] | tuple[str, ...],
        *,
        operation_id: str,
        context: str | None = None,
        min_observations: int = 2,
    ) -> dict[str, Any]:
        """Consolidate recurring co-activation into durable bidirectional links.

        Each operation contributes at most one observation per unordered pair.
        Links are created only after the pair has co-occurred enough times;
        fragment contents and provenance are never merged or rewritten.
        Retrying an operation ID with the same payload is idempotent.
        """
        self._ensure_open()
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        if isinstance(min_observations, bool) or not isinstance(min_observations, int) or min_observations < 1:
            raise ValueError("min_observations must be a positive integer")
        if context is not None and (not isinstance(context, str) or not context.strip()):
            raise ValueError("context must be a non-empty string when provided")
        if not isinstance(fragment_ids, (list, tuple)) or len(fragment_ids) < 2:
            raise ValueError("fragment_ids must contain at least two distinct IDs")
        if any(not isinstance(item, str) or not item.strip() for item in fragment_ids):
            raise ValueError("fragment IDs must be non-empty strings")
        ids = sorted(set(fragment_ids))
        if len(ids) < 2 or len(ids) != len(fragment_ids):
            raise ValueError("fragment_ids must contain at least two distinct IDs")
        context_key = context.strip().casefold() if context is not None else None
        payload_json = _json({
            "fragment_ids": ids,
            "context": context_key,
            "min_observations": min_observations,
        })
        pairs = [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))]
        self._db.execute("BEGIN IMMEDIATE")
        try:
            prior = self._db.execute(
                "SELECT payload_json, result_json FROM memory_association_observations WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if prior is not None:
                if prior["payload_json"] != payload_json:
                    raise ValueError("operation_id was already used with different coactivation")
                result = json.loads(prior["result_json"])
                self._db.commit()
                result["applied"] = False
                return result

            for fragment_id in ids:
                if self._db.execute(
                    "SELECT 1 FROM memory_fragments WHERE id = ?", (fragment_id,)
                ).fetchone() is None:
                    raise KeyError(f"unknown memory fragment: {fragment_id}")

            pair_results: list[dict[str, Any]] = []
            now = _now()
            for first, second in pairs:
                row = self._db.execute(
                    "SELECT observations, contexts_json FROM memory_association_evidence WHERE fragment_a = ? AND fragment_b = ?",
                    (first, second),
                ).fetchone()
                if row is None:
                    observations = 1
                    contexts = [context_key] if context_key is not None else []
                    self._db.execute(
                        "INSERT INTO memory_association_evidence "
                        "(fragment_a, fragment_b, observations, contexts_json, last_observed_at) VALUES (?, ?, ?, ?, ?)",
                        (first, second, observations, _json(contexts), now),
                    )
                else:
                    observations = int(row["observations"]) + 1
                    contexts = list(json.loads(row["contexts_json"]))
                    if context_key is not None and context_key not in contexts:
                        contexts.append(context_key)
                        contexts.sort()
                    self._db.execute(
                        "UPDATE memory_association_evidence SET observations = ?, contexts_json = ?, last_observed_at = ? "
                        "WHERE fragment_a = ? AND fragment_b = ?",
                        (observations, _json(contexts), now, first, second),
                    )
                linked = observations >= min_observations
                if linked:
                    self._link_without_commit(first, second)
                if context_key is not None:
                    self._db.execute(
                        "INSERT INTO memory_association_context_evidence "
                        "(fragment_a, fragment_b, context_key, observations, last_observed_at) "
                        "VALUES (?, ?, ?, 1, ?) "
                        "ON CONFLICT(fragment_a, fragment_b, context_key) DO UPDATE SET "
                        "observations = observations + 1, last_observed_at = excluded.last_observed_at",
                        (first, second, context_key, now),
                    )
                pair_results.append({
                    "fragment_a": first,
                    "fragment_b": second,
                    "observations": observations,
                    "contexts": contexts,
                    "linked": linked,
                })
            result = {"operation_id": operation_id, "pairs": pair_results, "applied": True}
            self._db.execute(
                "INSERT INTO memory_association_observations (operation_id, payload_json, result_json, created_at) "
                "VALUES (?, ?, ?, ?)",
                (operation_id, payload_json, _json(result), now),
            )
            self._db.commit()
            return result
        except Exception:
            self._db.rollback()
            raise

    def observe_sequence(
        self,
        fragment_ids: list[str] | tuple[str, ...],
        *,
        operation_id: str,
        context: str,
    ) -> dict[str, Any]:
        """Record ordered adjacent transitions between explicitly sequenced fragments.

        Unlike co-activation, order matters: A→B is distinct from B→A. The
        caller must provide a meaningful sequence; recall ranking is not treated
        as temporal order automatically. Each operation ID is idempotent.
        """
        self._ensure_open()
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        if not isinstance(fragment_ids, (list, tuple)) or len(fragment_ids) < 2:
            raise ValueError("fragment_ids must contain at least two IDs in sequence")
        if any(not isinstance(item, str) or not item.strip() for item in fragment_ids):
            raise ValueError("fragment IDs must be non-empty strings")
        ids = list(fragment_ids)
        for fragment_id in ids:
            self.get(fragment_id, record_access=False)
        context_key = context.strip().casefold()
        payload_json = _json({"fragment_ids": ids, "context": context_key})
        transitions = list(zip(ids, ids[1:]))
        self._db.execute("BEGIN IMMEDIATE")
        try:
            prior = self._db.execute(
                "SELECT payload_json, result_json FROM memory_sequence_batches WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if prior is not None:
                if prior["payload_json"] != payload_json:
                    raise ValueError("operation_id was already used with a different sequence payload")
                result = json.loads(prior["result_json"])
                self._db.commit()
                result["applied"] = False
                return result
            now = _now()
            for previous_id, next_id in transitions:
                self._db.execute(
                    """INSERT INTO memory_sequence_transitions
                    (previous_fragment_id, next_fragment_id, context_key, observations, last_observed_at)
                    VALUES (?, ?, ?, 1, ?)
                    ON CONFLICT(previous_fragment_id, next_fragment_id, context_key)
                    DO UPDATE SET observations = observations + 1, last_observed_at = excluded.last_observed_at""",
                    (previous_id, next_id, context_key, now),
                )
            result = {
                "operation_id": operation_id,
                "context": context_key,
                "transitions": [
                    {"previous_fragment_id": previous_id, "next_fragment_id": next_id}
                    for previous_id, next_id in transitions
                ],
                "applied": True,
            }
            self._db.execute(
                "INSERT INTO memory_sequence_batches(operation_id, payload_json, result_json, created_at) VALUES (?, ?, ?, ?)",
                (operation_id, payload_json, _json({k: v for k, v in result.items() if k != "applied"}), now),
            )
            self._db.commit()
            return result
        except Exception:
            self._db.rollback()
            raise

    def sequence_evidence(
        self, previous_fragment_id: str, next_fragment_id: str, *, context: str
    ) -> dict[str, Any] | None:
        """Return directional transition evidence for one context."""
        self._ensure_open()
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        row = self._db.execute(
            """SELECT observations, last_observed_at FROM memory_sequence_transitions
            WHERE previous_fragment_id = ? AND next_fragment_id = ? AND context_key = ?""",
            (previous_fragment_id, next_fragment_id, context.strip().casefold()),
        ).fetchone()
        if row is None:
            return None
        return {
            "previous_fragment_id": previous_fragment_id,
            "next_fragment_id": next_fragment_id,
            "context": context.strip().casefold(),
            "observations": int(row["observations"]),
            "last_observed_at": str(row["last_observed_at"]),
        }

    def sequence_strength(
        self, previous_fragment_id: str, next_fragment_id: str, *, context: str
    ) -> float:
        """Return a saturating directional transition strength in [0, 1]."""
        evidence = self.sequence_evidence(
            previous_fragment_id, next_fragment_id, context=context
        )
        if evidence is None:
            return 0.0
        strength_value = 1.0 - math.exp(-float(evidence["observations"]) / 2.0)
        row = self._db.execute(
            """SELECT score FROM memory_sequence_context_utility
            WHERE previous_fragment_id = ? AND next_fragment_id = ? AND context_key = ?""",
            (previous_fragment_id, next_fragment_id, context.strip().casefold()),
        ).fetchone()
        if row is not None:
            strength_value *= 2.0 * float(row["score"])
        return min(1.0, max(0.0, strength_value))

    def apply_sequence_feedback_batch(
        self,
        outcomes: Mapping[tuple[str, str], bool],
        *,
        context: str,
        operation_id: str,
        strength: float = 0.10,
    ) -> tuple[dict[tuple[str, str], float], bool]:
        """Adjust context-specific utility for observed directional transitions."""
        self._ensure_open()
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        context_key = context.strip().casefold()
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        amount = _score(strength, "strength")
        if not isinstance(outcomes, Mapping) or not outcomes:
            raise ValueError("outcomes must be a non-empty mapping")
        normalized: dict[tuple[str, str], bool] = {}
        for transition, useful in outcomes.items():
            if not isinstance(transition, tuple) or len(transition) != 2:
                raise ValueError("each transition key must be an ordered pair of fragment IDs")
            previous_id, next_id = transition
            if not isinstance(previous_id, str) or not previous_id.strip() or not isinstance(next_id, str) or not next_id.strip():
                raise ValueError("transition fragment IDs must be non-empty strings")
            if previous_id == next_id:
                raise ValueError("a fragment cannot transition to itself")
            if not isinstance(useful, bool):
                raise ValueError("every usefulness label must be boolean")
            normalized[(previous_id, next_id)] = useful
        payload_json = _json({
            "context": context_key,
            "outcomes": [
                {"transition": list(key), "useful": useful}
                for key, useful in sorted(normalized.items())
            ],
            "strength": amount,
        })
        self._db.execute("BEGIN IMMEDIATE")
        try:
            prior = self._db.execute(
                "SELECT payload_json, result_json FROM memory_sequence_feedback_batches WHERE operation_id = ?",
                (operation_id,),
            ).fetchone()
            if prior is not None:
                if prior["payload_json"] != payload_json:
                    raise ValueError("operation_id was already used with different sequence feedback")
                saved = json.loads(prior["result_json"])
                self._db.commit()
                return {(x["transition"][0], x["transition"][1]): float(x["score"]) for x in saved}, False
            results: list[dict[str, Any]] = []
            now = _now()
            for transition, useful in sorted(normalized.items()):
                previous_id, next_id = transition
                evidence = self._db.execute(
                    """SELECT 1 FROM memory_sequence_transitions
                    WHERE previous_fragment_id = ? AND next_fragment_id = ? AND context_key = ?""",
                    (previous_id, next_id, context_key),
                ).fetchone()
                if evidence is None:
                    raise KeyError(f"unknown sequence transition: {previous_id} -> {next_id} in {context_key}")
                row = self._db.execute(
                    """SELECT score FROM memory_sequence_context_utility
                    WHERE previous_fragment_id = ? AND next_fragment_id = ? AND context_key = ?""",
                    (previous_id, next_id, context_key),
                ).fetchone()
                before = float(row["score"]) if row is not None else 0.5
                after = min(1.0, max(0.0, before + (amount if useful else -amount)))
                results.append({"transition": [previous_id, next_id], "useful": useful, "score": after})
            for item in results:
                previous_id, next_id = item["transition"]
                self._db.execute(
                    """INSERT INTO memory_sequence_context_utility
                    (previous_fragment_id, next_fragment_id, context_key, score, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(previous_fragment_id, next_fragment_id, context_key)
                    DO UPDATE SET score = excluded.score, updated_at = excluded.updated_at""",
                    (previous_id, next_id, context_key, item["score"], now),
                )
            self._db.execute(
                "INSERT INTO memory_sequence_feedback_batches(operation_id, payload_json, result_json, created_at) VALUES (?, ?, ?, ?)",
                (operation_id, payload_json, _json(results), now),
            )
            self._db.commit()
            return {(x["transition"][0], x["transition"][1]): float(x["score"]) for x in results}, True
        except Exception:
            self._db.rollback()
            raise

    def association_evidence(self, fragment_id: str, related_id: str) -> dict[str, Any] | None:
        """Return accumulated co-activation evidence for a pair, if observed."""
        self._ensure_open()
        if not isinstance(fragment_id, str) or not fragment_id.strip():
            raise ValueError("fragment_id must be a non-empty string")
        if not isinstance(related_id, str) or not related_id.strip():
            raise ValueError("related_id must be a non-empty string")
        if fragment_id == related_id:
            raise ValueError("a fragment cannot be associated with itself")
        first, second = sorted((fragment_id, related_id))
        row = self._db.execute(
            "SELECT observations, contexts_json, last_observed_at FROM memory_association_evidence "
            "WHERE fragment_a = ? AND fragment_b = ?",
            (first, second),
        ).fetchone()
        if row is None:
            return None
        return {
            "fragment_a": first,
            "fragment_b": second,
            "observations": int(row["observations"]),
            "contexts": json.loads(row["contexts_json"]),
            "last_observed_at": str(row["last_observed_at"]),
        }

    def association_strength(
        self,
        fragment_id: str,
        related_id: str,
        *,
        context: str | None = None,
        as_of: datetime | None = None,
        half_life_seconds: float | None = None,
    ) -> float:
        """Return evidence-weighted association influence in [0, 1].

        Evidence strength saturates with repeated co-activation, while optional
        temporal decay reduces its influence without deleting the association
        or its audit evidence. Manually created legacy links without evidence
        return 1.0 to preserve their previous behavior.
        """
        self._ensure_open()
        if not isinstance(fragment_id, str) or not fragment_id.strip():
            raise ValueError("fragment_id must be a non-empty string")
        if not isinstance(related_id, str) or not related_id.strip():
            raise ValueError("related_id must be a non-empty string")
        if fragment_id == related_id:
            raise ValueError("a fragment cannot be associated with itself")
        if context is not None and (not isinstance(context, str) or not context.strip()):
            raise ValueError("context must be a non-empty string when provided")
        context_key = context.strip().casefold() if context is not None else None
        half_life = (
            self.association_decay_half_life_seconds
            if half_life_seconds is None else half_life_seconds
        )
        if half_life is not None and (
            isinstance(half_life, bool)
            or not isinstance(half_life, (int, float))
            or not math.isfinite(half_life)
            or half_life <= 0
        ):
            raise ValueError("half_life_seconds must be a positive finite number")
        first, second = sorted((fragment_id, related_id))
        row = self._db.execute(
            "SELECT observations, last_observed_at FROM memory_association_evidence "
            "WHERE fragment_a = ? AND fragment_b = ?",
            (first, second),
        ).fetchone()
        if row is None:
            return 1.0
        if context_key is not None:
            contextual_row = self._db.execute(
                "SELECT observations, last_observed_at FROM memory_association_context_evidence "
                "WHERE fragment_a = ? AND fragment_b = ? AND context_key = ?",
                (first, second, context_key),
            ).fetchone()
            if contextual_row is None:
                return 0.0
            row = contextual_row
        observations = int(row["observations"])
        strength = 1.0 - math.exp(-observations / 2.0)
        if context_key is not None:
            utility_row = self._db.execute(
                "SELECT score FROM memory_association_context_utility "
                "WHERE fragment_a = ? AND fragment_b = ? AND context_key = ?",
                (first, second, context_key),
            ).fetchone()
            if utility_row is not None:
                # 0.5 is neutral, 1.0 doubles influence, 0.0 suppresses it.
                strength *= 2.0 * float(utility_row["score"])
        strength = min(1.0, max(0.0, strength))
        if half_life is None:
            return strength
        reference = as_of or datetime.now(timezone.utc)
        if not isinstance(reference, datetime) or reference.tzinfo is None or reference.utcoffset() is None:
            raise ValueError("as_of must be a timezone-aware datetime or None")
        observed_at = datetime.fromisoformat(str(row["last_observed_at"]))
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        elapsed = max(0.0, (reference - observed_at).total_seconds())
        return strength * math.pow(0.5, elapsed / float(half_life))

    def apply_association_feedback_batch(
        self,
        outcomes: Mapping[tuple[str, str], bool],
        *,
        context: str,
        operation_id: str,
        strength: float = 0.10,
    ) -> tuple[dict[tuple[str, str], float], bool]:
        """Adjust the utility of specific associations for one context.

        Positive outcomes raise the contextual utility score; negative outcomes
        lower it. Scores start neutral at 0.5 and clamp to [0, 1]. The evidence
        ledger and fragment records are never changed. Operation IDs are
        idempotent and cannot be reused with a different payload.
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
        normalized: dict[tuple[str, str], bool] = {}
        for pair, useful in outcomes.items():
            if not isinstance(pair, tuple) or len(pair) != 2:
                raise ValueError("each association key must be a pair of fragment IDs")
            left, right = pair
            if (
                not isinstance(left, str) or not left.strip()
                or not isinstance(right, str) or not right.strip()
            ):
                raise ValueError("association fragment IDs must be non-empty strings")
            if left == right:
                raise ValueError("a fragment cannot be associated with itself")
            if not isinstance(useful, bool):
                raise ValueError("every usefulness label must be boolean")
            normalized[tuple(sorted((left, right)))] = useful
        payload = {
            "context": context_key,
            "outcomes": [
                {"pair": list(pair), "useful": useful}
                for pair, useful in sorted(normalized.items())
            ],
            "strength": amount,
        }
        payload_json = _json(payload)
        self._db.execute("BEGIN IMMEDIATE")
        try:
            prior = self._db.execute(
                "SELECT payload_json, result_json FROM memory_association_feedback_batches "
                "WHERE operation_id = ?", (operation_id,)
            ).fetchone()
            if prior is not None:
                if prior["payload_json"] != payload_json:
                    raise ValueError("operation_id was already used with different association feedback")
                saved = json.loads(prior["result_json"])
                self._db.commit()
                return {
                    (item["pair"][0], item["pair"][1]): float(item["score"])
                    for item in saved
                }, False

            results: list[dict[str, Any]] = []
            now = _now()
            for pair, useful in sorted(normalized.items()):
                first, second = pair
                for fragment_id in pair:
                    exists = self._db.execute(
                        "SELECT 1 FROM memory_fragments WHERE id = ?", (fragment_id,)
                    ).fetchone()
                    if exists is None:
                        raise KeyError(f"unknown memory fragment: {fragment_id}")
                evidence = self._db.execute(
                    "SELECT 1 FROM memory_association_evidence WHERE fragment_a = ? AND fragment_b = ?",
                    pair,
                ).fetchone()
                if evidence is None:
                    raise KeyError(f"unknown association: {first}, {second}")
                row = self._db.execute(
                    "SELECT score FROM memory_association_context_utility "
                    "WHERE fragment_a = ? AND fragment_b = ? AND context_key = ?",
                    (first, second, context_key),
                ).fetchone()
                before = float(row["score"]) if row is not None else 0.5
                after = min(1.0, max(0.0, before + (amount if useful else -amount)))
                results.append({
                    "pair": [first, second], "useful": useful,
                    "before": before, "score": after,
                })

            for item in results:
                first, second = item["pair"]
                self._db.execute(
                    """INSERT INTO memory_association_context_utility
                    (fragment_a, fragment_b, context_key, score, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(fragment_a, fragment_b, context_key) DO UPDATE SET
                    score = excluded.score, updated_at = excluded.updated_at""",
                    (first, second, context_key, item["score"], now),
                )
            self._db.execute(
                "INSERT INTO memory_association_feedback_batches "
                "(operation_id, payload_json, result_json, created_at) VALUES (?, ?, ?, ?)",
                (operation_id, payload_json, _json(results), now),
            )
            self._db.commit()
            return {
                (item["pair"][0], item["pair"][1]): float(item["score"])
                for item in results
            }, True
        except Exception:
            self._db.rollback()
            raise

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
                str(row["fragment_id"]): self._effective_context_score(
                    float(row["score"]), str(row["updated_at"]), as_of=datetime.now(timezone.utc)
                )
                for row in self._db.execute(
                    "SELECT fragment_id, score, updated_at FROM memory_context_importance WHERE context_key = ?",
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
                # Evidence-backed links contribute in proportion to their
                # accumulated support. Legacy/manual links without evidence retain
                # their previous ranking behavior.
                strengths = [
                    self.association_strength(
                        source_id, related_id, context=context_key,
                        as_of=datetime.now(timezone.utc)
                    )
                    for source_id in direct_matches
                    if related_id in fragments[source_id].related_ids
                ]
                association_strength = max(strengths, default=1.0)
                score = (0.20 + 0.10 * fragment.importance + 0.05 * fragment.confidence) * association_strength
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
                    """INSERT INTO memory_context_feedback_events
                    (operation_id, fragment_id, context_key, useful, before_score, after_score, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        operation_id, fragment_id, context_key,
                        int(normalized[fragment_id]), values["before"], values["after"], now,
                    ),
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

    def context_feedback_history(
        self,
        fragment_id: str,
        context: str,
        *,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Return newest-first, append-only feedback events for one context.

        This audit trail explains how the current contextual score evolved;
        it never rewrites or removes prior events.
        """
        self._ensure_open()
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        self.get(fragment_id, record_access=False)
        rows = self._db.execute(
            """SELECT operation_id, fragment_id, context_key, useful,
                      before_score, after_score, created_at
               FROM memory_context_feedback_events
               WHERE fragment_id = ? AND context_key = ?
               ORDER BY event_id DESC LIMIT ?""",
            (fragment_id, context.strip().casefold(), limit),
        ).fetchall()
        return [
            {
                "operation_id": str(row["operation_id"]),
                "fragment_id": str(row["fragment_id"]),
                "context": str(row["context_key"]),
                "useful": bool(row["useful"]),
                "before_score": float(row["before_score"]),
                "after_score": float(row["after_score"]),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

    def context_importance(
        self,
        fragment_id: str,
        context: str,
        *,
        as_of: datetime | None = None,
        half_life_seconds: float | None = None,
    ) -> float:
        """Return effective task-relative relevance, decaying toward neutral.

        Decay is opt-in through the constructor or half_life_seconds.
        as_of is injectable for deterministic tests and simulations. Reads
        never rewrite the stored score or its feedback audit trail.
        """
        self._ensure_open()
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        self.get(fragment_id, record_access=False)
        row = self._db.execute(
            "SELECT score, updated_at FROM memory_context_importance WHERE fragment_id = ? AND context_key = ?",
            (fragment_id, context.strip().casefold()),
        ).fetchone()
        if row is None:
            return 0.5
        return self._effective_context_score(
            float(row["score"]), str(row["updated_at"]), as_of=as_of,
            half_life_seconds=half_life_seconds,
        )

    def _effective_context_score(
        self,
        score: float,
        updated_at: str,
        *,
        as_of: datetime | None = None,
        half_life_seconds: float | None = None,
    ) -> float:
        half_life = (
            self.context_decay_half_life_seconds
            if half_life_seconds is None else half_life_seconds
        )
        if half_life is None:
            return score
        if (
            isinstance(half_life, bool)
            or not isinstance(half_life, (int, float))
            or not math.isfinite(half_life)
            or half_life <= 0
        ):
            raise ValueError("half_life_seconds must be a positive finite number")
        reference = as_of or datetime.now(timezone.utc)
        if not isinstance(reference, datetime):
            raise ValueError("as_of must be a datetime or None")
        if reference.tzinfo is None or reference.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        stored_at = datetime.fromisoformat(updated_at)
        if stored_at.tzinfo is None or stored_at.utcoffset() is None:
            stored_at = stored_at.replace(tzinfo=timezone.utc)
        elapsed = max(0.0, (reference - stored_at).total_seconds())
        retention = math.pow(0.5, elapsed / float(half_life))
        return 0.5 + (score - 0.5) * retention

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
