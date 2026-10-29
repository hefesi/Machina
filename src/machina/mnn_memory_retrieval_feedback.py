"""Outcome feedback for retrieval relevance in the MNN fragment archive.

Feedback adjusts retrieval importance only. It does not alter content,
provenance, confidence, associations, or pinned status.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .fragment_memory import FragmentMemory, MemoryFragment


@dataclass(frozen=True, slots=True)
class MemoryFeedbackResult:
    """Auditable result of applying one relevance-feedback event."""

    fragment_id: str
    useful: bool
    strength: float
    importance_before: float
    importance_after: float


class MNNMemoryRetrievalFeedback:
    """Apply explicit usefulness feedback to an existing memory fragment.

    Positive feedback raises importance; negative feedback lowers it.
    Negative feedback means "less useful for retrieval", not "factually false".
    """

    schema_version = 1

    def __init__(self, memory: FragmentMemory, *, default_strength: float = 0.10) -> None:
        if isinstance(default_strength, bool) or not isinstance(default_strength, (int, float)):
            raise ValueError("default_strength must be a finite number in [0, 1]")
        strength = float(default_strength)
        if not math.isfinite(strength) or not 0.0 <= strength <= 1.0:
            raise ValueError("default_strength must be a finite number in [0, 1]")
        self.memory = memory
        self.default_strength = strength

    def apply(self, fragment_id: str, *, useful: bool, strength: float | None = None) -> tuple[MemoryFragment, MemoryFeedbackResult]:
        """Persist one explicit usefulness signal and return the updated fragment."""
        if not isinstance(useful, bool):
            raise ValueError("useful must be boolean")
        amount = self.default_strength if strength is None else strength
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("strength must be a finite number in [0, 1]")
        amount = float(amount)
        if not math.isfinite(amount) or not 0.0 <= amount <= 1.0:
            raise ValueError("strength must be a finite number in [0, 1]")

        before = self.memory.get(fragment_id, record_access=False)
        delta = amount if useful else -amount
        after = self.memory.reinforce(fragment_id, importance_delta=delta)
        event = MemoryFeedbackResult(fragment_id, useful, amount, before.importance, after.importance)
        return after, event
