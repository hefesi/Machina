"""Outcome feedback for retrieval relevance in the MNN fragment archive.

Feedback adjusts retrieval importance only. It does not alter content,
provenance, confidence, associations, or pinned status.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Mapping

from .fragment_memory import FragmentMemory, MemoryFragment


@dataclass(frozen=True, slots=True)
class MemoryFeedbackResult:
    """Auditable result of applying one relevance-feedback event."""

    fragment_id: str
    useful: bool
    strength: float
    importance_before: float
    importance_after: float
    feedback_id: str | None = None
    applied: bool = True


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

    def apply_many(
        self,
        outcomes: Mapping[str, bool],
        *,
        strength: float | None = None,
        feedback_id: str | None = None,
    ) -> tuple[tuple[MemoryFragment, MemoryFeedbackResult], ...]:
        """Apply explicit per-fragment usefulness labels after validating all IDs.

        This is intentionally not a blanket reward for every recalled item:
        callers must identify which fragments were useful. All IDs and labels
        are checked before the first update so an unknown ID cannot cause a
        partially applied batch.
        """
        if not isinstance(outcomes, Mapping):
            raise ValueError("outcomes must map fragment IDs to boolean usefulness labels")
        normalized = list(outcomes.items())
        if not normalized:
            raise ValueError("outcomes must not be empty")
        for fragment_id, useful in normalized:
            if not isinstance(fragment_id, str) or not fragment_id.strip():
                raise ValueError("fragment IDs must be non-empty strings")
            if not isinstance(useful, bool):
                raise ValueError("every usefulness label must be boolean")
        if feedback_id is not None:
            if not isinstance(feedback_id, str) or not feedback_id.strip():
                raise ValueError("feedback_id must be a non-empty string")
            amount = self.default_strength if strength is None else strength
            if isinstance(amount, bool) or not isinstance(amount, (int, float)):
                raise ValueError("strength must be a finite number in [0, 1]")
            amount = float(amount)
            if not math.isfinite(amount) or not 0.0 <= amount <= 1.0:
                raise ValueError("strength must be a finite number in [0, 1]")
            deltas = {
                fragment_id: amount if useful else -amount
                for fragment_id, useful in normalized
            }
            fragments, audit, applied = self.memory.apply_importance_feedback_batch(
                deltas, operation_id=feedback_id
            )
            return tuple(
                (
                    fragments[fragment_id],
                    MemoryFeedbackResult(
                        fragment_id=fragment_id,
                        useful=useful,
                        strength=amount,
                        importance_before=audit[fragment_id]["before"],
                        importance_after=audit[fragment_id]["after"],
                        feedback_id=feedback_id,
                        applied=applied,
                    ),
                )
                for fragment_id, useful in normalized
            )

        # Validate the entire batch before mutating any fragment.
        for fragment_id, _ in normalized:
            self.memory.get(fragment_id, record_access=False)
        return tuple(
            self.apply(fragment_id, useful=useful, strength=strength)
            for fragment_id, useful in normalized
        )

    def apply(self, fragment_id: str, *, useful: bool, strength: float | None = None, feedback_id: str | None = None) -> tuple[MemoryFragment, MemoryFeedbackResult]:
        """Persist one explicit usefulness signal and return the updated fragment."""
        if not isinstance(useful, bool):
            raise ValueError("useful must be boolean")
        if feedback_id is not None:
            return self.apply_many({fragment_id: useful}, strength=strength, feedback_id=feedback_id)[0]
        amount = self.default_strength if strength is None else strength
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise ValueError("strength must be a finite number in [0, 1]")
        amount = float(amount)
        if not math.isfinite(amount) or not 0.0 <= amount <= 1.0:
            raise ValueError("strength must be a finite number in [0, 1]")

        before = self.memory.get(fragment_id, record_access=False)
        # Pinning protects retention and active-view priority; it does not
        # freeze task relevance. A pinned fragment can become less useful for
        # one retrieval context without being removed or unpinned.
        delta = amount if useful else -amount
        after = self.memory.reinforce(fragment_id, importance_delta=delta)
        event = MemoryFeedbackResult(fragment_id, useful, amount, before.importance, after.importance, feedback_id=None, applied=True)
        return after, event
