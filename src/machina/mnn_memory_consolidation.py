"""Deterministic short-/long-term memory projection over FragmentMemory.

Consolidation classifies existing records; it never duplicates or deletes them.
The archive remains the source of truth, while each call derives an auditable
priority score and tier from importance, confidence, retrieval frequency,
recency, and explicit pinning.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from typing import Literal

from .fragment_memory import FragmentMemory, MemoryFragment

MemoryTier = Literal["short_term", "long_term"]


def _unit_interval(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number in [0, 1]")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be a finite number in [0, 1]")
    return result


@dataclass(frozen=True, slots=True)
class ConsolidatedMemory:
    """A scored view of one archived fragment; the fragment itself is unchanged."""

    fragment: MemoryFragment
    score: float
    tier: MemoryTier
    reasons: tuple[str, ...]


class MNNMemoryConsolidator:
    """Rank archived fragments into active short-term and durable long-term views.

    The score is an explicit engineering heuristic, not a biological memory
    model. Long-term classification is based on pinning, stable importance, or
    repeated access plus a score threshold. A low score only affects ranking;
    it never deletes a record or mutates the archive.
    """

    schema_version = 1

    def __init__(
        self,
        memory: FragmentMemory,
        *,
        decay_per_day: float = 0.04,
        importance_weight: float = 0.45,
        confidence_weight: float = 0.15,
        usage_weight: float = 0.20,
        recency_weight: float = 0.20,
        access_saturation: int = 8,
        durable_importance: float = 0.80,
        durable_score: float = 0.55,
        consolidation_accesses: int = 3,
    ) -> None:
        self.memory = memory
        self.decay_per_day = _unit_interval(decay_per_day, "decay_per_day")
        self.importance_weight = _unit_interval(importance_weight, "importance_weight")
        self.confidence_weight = _unit_interval(confidence_weight, "confidence_weight")
        self.usage_weight = _unit_interval(usage_weight, "usage_weight")
        self.recency_weight = _unit_interval(recency_weight, "recency_weight")
        if not math.isclose(
            self.importance_weight + self.confidence_weight + self.usage_weight + self.recency_weight,
            1.0, abs_tol=1e-9,
        ):
            raise ValueError("score weights must sum to 1")
        if isinstance(access_saturation, bool) or not isinstance(access_saturation, int) or access_saturation < 1:
            raise ValueError("access_saturation must be a positive integer")
        if isinstance(consolidation_accesses, bool) or not isinstance(consolidation_accesses, int) or consolidation_accesses < 1:
            raise ValueError("consolidation_accesses must be a positive integer")
        self.access_saturation = access_saturation
        self.consolidation_accesses = consolidation_accesses
        self.durable_importance = _unit_interval(durable_importance, "durable_importance")
        self.durable_score = _unit_interval(durable_score, "durable_score")

    def score(self, fragment: MemoryFragment, *, now: datetime | None = None) -> float:
        """Calculate a bounded priority score for one fragment at a given time."""
        instant = now or datetime.now(timezone.utc)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        last_access = datetime.fromisoformat(fragment.last_accessed_at)
        if last_access.tzinfo is None or last_access.utcoffset() is None:
            raise ValueError("fragment last_accessed_at must be timezone-aware")
        age_days = max(0.0, (instant.astimezone(timezone.utc) - last_access.astimezone(timezone.utc)).total_seconds() / 86400)
        recency = math.exp(-self.decay_per_day * age_days)
        usage = min(1.0, math.log1p(fragment.access_count) / math.log1p(self.access_saturation))
        value = (
            self.importance_weight * fragment.importance
            + self.confidence_weight * fragment.confidence
            + self.usage_weight * usage
            + self.recency_weight * recency
        )
        return min(1.0, max(0.0, value))

    def consolidate(
        self,
        *,
        limit: int | None = None,
        now: datetime | None = None,
    ) -> list[ConsolidatedMemory]:
        """Return an ordered projection without changing or removing archive rows.

        `limit` bounds the returned active projection, not storage. Pinned items
        classify as long-term and rank first; important or repeatedly accessed
        records can also enter long-term memory even when they are old.
        """
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            raise ValueError("limit must be a positive integer or None")
        instant = now or datetime.now(timezone.utc)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("now must be timezone-aware")
        ranked: list[ConsolidatedMemory] = []
        for fragment in self.memory.archive():
            score = self.score(fragment, now=instant)
            reasons: list[str] = []
            if fragment.pinned:
                reasons.append("pinned")
            if fragment.importance >= self.durable_importance:
                reasons.append("high_importance")
            if fragment.access_count >= self.consolidation_accesses:
                reasons.append("repeated_access")
            if score >= self.durable_score:
                reasons.append("score_threshold")
            long_term = fragment.pinned or fragment.importance >= self.durable_importance or (
                fragment.access_count >= self.consolidation_accesses and score >= self.durable_score
            )
            tier: MemoryTier = "long_term" if long_term else "short_term"
            if not reasons:
                reasons.append("recent_or_low_stability")
            ranked.append(ConsolidatedMemory(fragment, score, tier, tuple(reasons)))
        ranked.sort(key=lambda item: (
            0 if item.tier == "long_term" else 1,
            -item.score,
            -item.fragment.importance,
            item.fragment.created_at,
            item.fragment.id,
        ))
        return ranked if limit is None else ranked[:limit]

    def snapshot(self) -> dict:
        """Serialize policy configuration; fragment records stay in SQLite."""
        return {
            "schema_version": self.schema_version,
            "decay_per_day": self.decay_per_day,
            "importance_weight": self.importance_weight,
            "confidence_weight": self.confidence_weight,
            "usage_weight": self.usage_weight,
            "recency_weight": self.recency_weight,
            "access_saturation": self.access_saturation,
            "durable_importance": self.durable_importance,
            "durable_score": self.durable_score,
            "consolidation_accesses": self.consolidation_accesses,
        }

    @classmethod
    def from_snapshot(cls, data: dict, memory: FragmentMemory) -> "MNNMemoryConsolidator":
        if not isinstance(data, dict) or data.get("schema_version") != cls.schema_version:
            raise ValueError("unsupported MNN memory-consolidator snapshot schema")
        return cls(
            memory,
            decay_per_day=data["decay_per_day"],
            importance_weight=data["importance_weight"],
            confidence_weight=data["confidence_weight"],
            usage_weight=data["usage_weight"],
            recency_weight=data["recency_weight"],
            access_saturation=data["access_saturation"],
            durable_importance=data["durable_importance"],
            durable_score=data["durable_score"],
            consolidation_accesses=data["consolidation_accesses"],
        )
