"""Non-destructive review of explicitly identified memory conflicts.

The relationship between statements is supplied by an external evaluator.
This module does not claim semantic contradiction detection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .fragment_memory import FragmentMemory


Relationship = Literal["contradicts", "supports", "contextualizes", "unrelated", "uncertain"]


@dataclass(frozen=True, slots=True)
class MemoryConflictReview:
    fragment_id: str
    prior_content: str
    incoming_content: str
    relationship: Relationship
    evidence_id: str
    context_refs: tuple[str, ...]
    recommendation: str
    rationale: str


class MNNMemoryConflictReviewer:
    """Produce a side-effect-free disposition for a new statement vs. memory."""

    _RELATIONSHIPS = {
        "contradicts", "supports", "contextualizes", "unrelated", "uncertain",
    }

    def review(
        self,
        memory: FragmentMemory,
        fragment_id: str,
        incoming_content: str,
        *,
        relationship: Relationship,
        evidence_id: str,
        context_refs: tuple[str, ...] = (),
    ) -> MemoryConflictReview:
        if not isinstance(memory, FragmentMemory):
            raise TypeError("memory must be a FragmentMemory")
        for name, value in (
            ("fragment_id", fragment_id),
            ("incoming_content", incoming_content),
            ("evidence_id", evidence_id),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if relationship not in self._RELATIONSHIPS:
            raise ValueError(f"relationship must be one of {sorted(self._RELATIONSHIPS)}")
        if isinstance(context_refs, (str, bytes)) or not isinstance(context_refs, (tuple, list)):
            raise TypeError("context_refs must be a tuple or list")
        if any(not isinstance(ref, str) or not ref.strip() for ref in context_refs):
            raise ValueError("context_refs must contain non-empty strings")
        prior = memory.get(fragment_id, record_access=False)
        recommendations = {
            "contradicts": (
                "needs_review",
                "Conflicting claims require source, scope, and time comparison; keep both records intact.",
            ),
            "supports": (
                "corroborate_without_rewrite",
                "The incoming statement supports the existing record; preserve provenance separately.",
            ),
            "contextualizes": (
                "preserve_both",
                "The statements may apply under different conditions; retain both contexts.",
            ),
            "unrelated": (
                "no_conflict",
                "No conflict was declared by the external evaluator.",
            ),
            "uncertain": (
                "defer",
                "Insufficient basis to classify the relationship; do not revise the memory.",
            ),
        }
        recommendation, rationale = recommendations[relationship]
        return MemoryConflictReview(
            fragment_id=fragment_id,
            prior_content=prior.content,
            incoming_content=incoming_content.strip(),
            relationship=relationship,
            evidence_id=evidence_id,
            context_refs=tuple(sorted(set(context_refs))),
            recommendation=recommendation,
            rationale=rationale,
        )
