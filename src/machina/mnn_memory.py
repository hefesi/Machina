"""Priority-weighted fragment memory for the experimental MNN substrate.

This is an explicit, deterministic memory policy, not a model of human memory.
Fragments remain separate records; retrieval reinforces relevant fragments and
optional decay reduces low-priority strength without silently deleting data.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Iterable, Mapping


def _finite(value: float, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.casefold(), flags=re.UNICODE))


@dataclass
class MemoryFragment:
    """One independently addressable information fragment."""
    id: str
    content: str
    importance: float = 0.5
    strength: float = 1.0
    created_at: int = 0
    last_accessed: int = 0
    access_count: int = 0
    tags: tuple[str, ...] = ()
    protected: bool = False

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("fragment id cannot be empty")
        if not self.content.strip():
            raise ValueError("fragment content cannot be empty")
        self.importance = _finite(self.importance, "importance")
        self.strength = _finite(self.strength, "strength")
        if not 0.0 <= self.importance <= 1.0:
            raise ValueError("importance must be between 0 and 1")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError("strength must be between 0 and 1")
        for name in ("created_at", "last_accessed", "access_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        self.tags = tuple(str(tag) for tag in self.tags)


class PriorityMemory:
    """Bounded fragment store with relevance retrieval and controlled decay.

    Ranking combines lexical overlap, importance, and current strength.
    The store never deletes fragments as a side effect of decay; pruning is an
    explicit operation and protected/high-importance fragments are retained.
    """
    SCHEMA_VERSION = 1

    def __init__(self, *, capacity: int = 1000, retention_floor: float = 0.05) -> None:
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 1:
            raise ValueError("capacity must be a positive integer")
        self.retention_floor = _finite(retention_floor, "retention_floor")
        if not 0.0 <= self.retention_floor <= 1.0:
            raise ValueError("retention_floor must be between 0 and 1")
        self.capacity = capacity
        self.fragments: dict[str, MemoryFragment] = {}
        self.clock = 0

    def remember(self, fragment: MemoryFragment) -> None:
        """Insert or update a fragment; at capacity, evict the lowest priority."""
        existing = self.fragments.get(fragment.id)
        if existing is not None:
            fragment.access_count = max(fragment.access_count, existing.access_count)
            fragment.created_at = min(fragment.created_at, existing.created_at)
            self.fragments[fragment.id] = fragment
            return
        if len(self.fragments) >= self.capacity:
            candidates = [f for f in self.fragments.values() if not f.protected and f.importance < 0.95]
            if not candidates:
                raise OverflowError("memory is full of protected/high-importance fragments")
            victim = min(candidates, key=lambda f: (self.priority(f), f.created_at, f.id))
            del self.fragments[victim.id]
        self.fragments[fragment.id] = fragment
        self.clock = max(self.clock, fragment.created_at, fragment.last_accessed)

    @staticmethod
    def priority(fragment: MemoryFragment) -> float:
        """Priority score in [0, 1], combining importance and retained strength."""
        return fragment.importance * 0.7 + fragment.strength * 0.3

    def retrieve(self, query: str, *, limit: int = 5, now: int | None = None) -> list[MemoryFragment]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
            raise ValueError("limit must be a non-negative integer")
        query_tokens = _tokens(query)
        timestamp = self.clock + 1 if now is None else now
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < self.clock:
            raise ValueError("now must be an integer not earlier than the memory clock")
        self.clock = timestamp
        scored: list[tuple[float, str, MemoryFragment]] = []
        for fragment in self.fragments.values():
            content_tokens = _tokens(fragment.content) | _tokens(" ".join(fragment.tags))
            overlap = len(query_tokens & content_tokens) / max(1, len(query_tokens))
            score = 0.65 * overlap + 0.25 * fragment.importance + 0.10 * fragment.strength
            scored.append((score, fragment.id, fragment))
        scored.sort(key=lambda item: (-item[0], item[1]))
        results = [fragment for score, _, fragment in scored if score > 0][:limit]
        for fragment in results:
            fragment.access_count += 1
            fragment.last_accessed = timestamp
            fragment.strength = min(1.0, fragment.strength + 0.03)
        return results

    def decay(self, *, rate: float = 0.01, steps: int = 1) -> dict[str, float]:
        """Reduce strength gradually; importance slows decay and protected items do not decay."""
        rate = _finite(rate, "rate")
        if not 0.0 <= rate <= 1.0:
            raise ValueError("rate must be between 0 and 1")
        if isinstance(steps, bool) or not isinstance(steps, int) or steps < 0:
            raise ValueError("steps must be a non-negative integer")
        changes: dict[str, float] = {}
        for fragment in self.fragments.values():
            old = fragment.strength
            if not fragment.protected:
                effective_rate = rate * (1.0 - fragment.importance)
                fragment.strength = max(self.retention_floor, old * ((1.0 - effective_rate) ** steps))
            changes[fragment.id] = fragment.strength - old
        self.clock += steps
        return changes

    def prune(self, *, min_priority: float = 0.1, max_remove: int | None = None) -> list[str]:
        """Explicitly remove low-priority fragments, preserving protected/critical records."""
        threshold = _finite(min_priority, "min_priority")
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("min_priority must be between 0 and 1")
        if max_remove is not None and (
            isinstance(max_remove, bool) or not isinstance(max_remove, int) or max_remove < 0
        ):
            raise ValueError("max_remove must be a non-negative integer or None")
        candidates = sorted(
            (f for f in self.fragments.values()
             if not f.protected and f.importance < 0.95 and self.priority(f) < threshold),
            key=lambda f: (self.priority(f), f.last_accessed, f.id),
        )
        if max_remove is not None:
            candidates = candidates[:max_remove]
        for fragment in candidates:
            del self.fragments[fragment.id]
        return [fragment.id for fragment in candidates]

    def snapshot(self) -> dict:
        return {
            "schema_version": self.SCHEMA_VERSION,
            "capacity": self.capacity,
            "retention_floor": self.retention_floor,
            "clock": self.clock,
            "fragments": [
                {**vars(fragment), "tags": list(fragment.tags)}
                for fragment in self.fragments.values()
            ],
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "PriorityMemory":
        if data.get("schema_version") != cls.SCHEMA_VERSION:
            raise ValueError("unsupported memory snapshot schema")
        memory = cls(capacity=data["capacity"], retention_floor=data["retention_floor"])
        for item in data["fragments"]:
            fragment_data = dict(item)
            fragment_data["tags"] = tuple(fragment_data.get("tags", ()))
            memory.remember(MemoryFragment(**fragment_data))
        memory.clock = int(data["clock"])
        if memory.clock < 0:
            raise ValueError("clock cannot be negative")
        return memory
