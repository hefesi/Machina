"""Evidence-grounded concept candidates from recurring memory tags.

This module builds small, inspectable hypotheses rather than pretending to
understand arbitrary prose. A concept is supported by multiple source fragments
that share an explicit tag. Contradiction is reported only when the evidence
records an explicit metadata polarity; absence of polarity is not treated as
agreement or disagreement.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from typing import Literal

from .fragment_memory import FragmentMemory, MemoryFragment

Polarity = Literal["supports", "contradicts", "unknown"]


def _polarity(fragment: MemoryFragment) -> Polarity:
    value = fragment.metadata.get("polarity", "unknown")
    if value not in {"supports", "contradicts", "unknown"}:
        return "unknown"
    return value  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class ConceptHypothesis:
    """A transparent candidate pattern grounded in source fragment IDs."""

    key: str
    label: str
    evidence_ids: tuple[str, ...]
    support_count: int
    confidence: float
    status: Literal["supported", "conflicted", "insufficient"]
    supporting_ids: tuple[str, ...]
    contradicting_ids: tuple[str, ...]
    unknown_polarity_ids: tuple[str, ...]


class MNNConceptBuilder:
    """Derive recurring tag-based concepts without rewriting source evidence."""

    schema_version = 1

    def __init__(self, memory: FragmentMemory, *, min_support: int = 2) -> None:
        if isinstance(min_support, bool) or not isinstance(min_support, int) or min_support < 2:
            raise ValueError("min_support must be an integer of at least 2")
        self.memory = memory
        self.min_support = min_support

    def discover(self, *, include_kinds: tuple[str, ...] = ("fact", "experience")) -> list[ConceptHypothesis]:
        """Group non-derived evidence by explicit tags and report support/conflict.

        Confidence combines mean source confidence with a bounded support factor.
        It is a ranking heuristic, not a calibrated probability. Concept fragments
        themselves are excluded to prevent recursive self-confirmation.
        """
        if not include_kinds or not all(isinstance(kind, str) and kind.strip() for kind in include_kinds):
            raise ValueError("include_kinds must contain non-empty kind names")
        grouped: dict[str, list[MemoryFragment]] = {}
        for fragment in self.memory.archive():
            if fragment.kind == "concept" or fragment.kind not in include_kinds:
                continue
            for tag in set(fragment.tags):
                key = " ".join(tag.casefold().split())
                if key:
                    grouped.setdefault(key, []).append(fragment)
        hypotheses: list[ConceptHypothesis] = []
        for key, records in grouped.items():
            records.sort(key=lambda item: item.id)
            if len(records) < self.min_support:
                continue
            supporting = tuple(item.id for item in records if _polarity(item) == "supports")
            contradicting = tuple(item.id for item in records if _polarity(item) == "contradicts")
            unknown = tuple(item.id for item in records if _polarity(item) == "unknown")
            if supporting and contradicting:
                status: Literal["supported", "conflicted", "insufficient"] = "conflicted"
            elif len(supporting) >= self.min_support:
                status = "supported"
            else:
                status = "insufficient"
            mean_confidence = sum(item.confidence for item in records) / len(records)
            support_factor = 1.0 - math.exp(-len(records) / self.min_support)
            confidence = min(1.0, max(0.0, mean_confidence * support_factor))
            hypotheses.append(ConceptHypothesis(
                key=key,
                label=f"Recurring pattern: {key}",
                evidence_ids=tuple(item.id for item in records),
                support_count=len(records),
                confidence=confidence,
                status=status,
                supporting_ids=supporting,
                contradicting_ids=contradicting,
                unknown_polarity_ids=unknown,
            ))
        hypotheses.sort(key=lambda item: (item.status == "conflicted", -item.support_count, -item.confidence, item.key))
        return hypotheses

    def materialize(self, hypothesis: ConceptHypothesis) -> MemoryFragment:
        """Persist one derived concept with provenance; identical evidence is idempotent."""
        if not isinstance(hypothesis, ConceptHypothesis):
            raise ValueError("hypothesis must be a ConceptHypothesis")
        if not hypothesis.evidence_ids or any(not isinstance(item, str) or not item.strip() for item in hypothesis.evidence_ids):
            raise ValueError("hypothesis must reference evidence fragment IDs")
        existing_ids = {fragment.id for fragment in self.memory.archive()}
        missing = set(hypothesis.evidence_ids) - existing_ids
        if missing:
            raise ValueError(f"hypothesis references missing evidence: {', '.join(sorted(missing))}")
        digest_input = "|".join((hypothesis.key, *sorted(hypothesis.evidence_ids)))
        identifier = "concept_" + hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:24]
        try:
            return self.memory.get(identifier, record_access=False)
        except KeyError:
            pass
        return self.memory.add(
            hypothesis.label,
            kind="concept",
            source_uri="mnn://concept-builder/v1",
            importance=min(1.0, 0.35 + 0.1 * hypothesis.support_count),
            confidence=hypothesis.confidence,
            tags=(hypothesis.key, "derived-concept", hypothesis.status),
            related_ids=hypothesis.evidence_ids,
            metadata={
                "concept_key": hypothesis.key,
                "status": hypothesis.status,
                "support_count": hypothesis.support_count,
                "evidence_ids": list(hypothesis.evidence_ids),
                "supporting_ids": list(hypothesis.supporting_ids),
                "contradicting_ids": list(hypothesis.contradicting_ids),
                "unknown_polarity_ids": list(hypothesis.unknown_polarity_ids),
                "confidence_is_calibrated_probability": False,
                "builder_schema_version": self.schema_version,
            },
            fragment_id=identifier,
        )

    def consolidate(self) -> list[MemoryFragment]:
        """Discover and persist all current hypotheses, returning derived records."""
        return [self.materialize(item) for item in self.discover()]
