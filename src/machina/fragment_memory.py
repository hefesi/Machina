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
            score = self._priority(fragment, now, requested_tags=requested)
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
    ) -> list[MemoryFragment]:
        """Retrieve fragments by lexical overlap and optionally one-hop associations.

        This is an explainable lexical baseline, not semantic understanding. A
        related fragment may be returned as context even when its own wording
        does not overlap the query. Retrieval never deletes or rewrites memory.
        """
        self._ensure_open()
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        import re

        def tokens(text: str) -> set[str]:
            return {token.casefold() for token in re.findall(r"\w+", text, flags=re.UNICODE) if len(token) > 1}

        query_tokens = tokens(query)
        if not query_tokens:
            return []
        rows = self._db.execute("SELECT * FROM memory_fragments").fetchall()
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
                ranked.append((score, related_id))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [fragments[fragment_id] for _, fragment_id in ranked[:limit]]

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

    def _priority(
        self,
        fragment: MemoryFragment,
        now: datetime,
        *,
        requested_tags: set[str] | None = None,
    ) -> float:
        """Compute the active-view score with the instance's configured policy.

        Reading a fragment, recalling it, or ranking an active view therefore
        reports the same priority for the same instant and tag context.
        """
        last_accessed = datetime.fromisoformat(fragment.last_accessed_at)
        age_days = max(0.0, (now - last_accessed).total_seconds() / 86400)
        decay = math.exp(-self.decay_per_day * age_days)
        usage = min(1.0, math.log1p(fragment.access_count) / 5.0) * self.usage_reinforcement
        requested = requested_tags or set()
        tag_bonus = 0.2 if requested and requested.intersection(
            tag.casefold() for tag in fragment.tags
        ) else 0.0
        score = min(1.0, fragment.importance * decay + usage + tag_bonus)
        return 1.0 if fragment.pinned else score

    def _from_row(self, row: sqlite3.Row) -> MemoryFragment:
        created = datetime.fromisoformat(str(row["created_at"]))
        last = datetime.fromisoformat(str(row["last_accessed_at"]))
        fragment = MemoryFragment(
            id=str(row["id"]), content=str(row["content"]), kind=str(row["kind"]),
            source_uri=str(row["source_uri"]), importance=float(row["importance"]),
            confidence=float(row["confidence"]), priority=0.0,
            access_count=int(row["access_count"]), created_at=created.isoformat(),
            last_accessed_at=last.isoformat(), pinned=bool(row["pinned"]),
            tags=tuple(json.loads(row["tags_json"])),
            related_ids=tuple(json.loads(row["related_ids_json"])),
            metadata=json.loads(row["metadata_json"]),
        )
        return self._with_priority(
            fragment, self._priority(fragment, datetime.now(timezone.utc))
        )

    @staticmethod
    def _with_priority(fragment: MemoryFragment, priority: float) -> MemoryFragment:
        from dataclasses import replace
        return replace(fragment, priority=priority)

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("fragment memory is closed")
