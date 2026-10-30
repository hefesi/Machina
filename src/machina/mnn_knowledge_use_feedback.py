"""Apply explicit, execution-confirmed feedback to contextual knowledge relevance.

This adapter never infers that evidence was useful from reward alone. A caller
must label each cited evidence fragment, and the proposed action must have been
confirmed as executed. FragmentMemory supplies atomic, idempotent persistence.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .fragment_memory import FragmentMemory


@dataclass(frozen=True, slots=True)
class KnowledgeUseFeedbackResult:
    """Auditable result of one contextual evidence-feedback batch."""

    context: str
    operation_id: str
    scores: tuple[tuple[str, float], ...]
    applied: bool


class MNNKnowledgeUseFeedback:
    """Adjust task-relative evidence relevance from explicit outcome labels."""

    def __init__(self, memory: FragmentMemory, *, strength: float = 0.1) -> None:
        if not isinstance(memory, FragmentMemory):
            raise ValueError("memory must be a FragmentMemory")
        if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not 0.0 < float(strength) <= 1.0:
            raise ValueError("strength must be a number within (0, 1]")
        self.memory = memory
        self.strength = float(strength)

    def apply(
        self,
        proposal: Mapping[str, object],
        usefulness: Mapping[str, bool],
        *,
        execution_confirmed: bool,
        executed_action: str,
        operation_id: str,
    ) -> KnowledgeUseFeedbackResult:
        """Apply caller-labelled usefulness to proposal evidence, once per operation.

        `usefulness` maps memory fragment IDs to explicit useful/not-useful labels.
        Reward magnitude is intentionally not converted into evidence labels.
        """
        if not isinstance(proposal, Mapping):
            raise ValueError("proposal must be a mapping")
        if proposal.get("status") != "proposed":
            raise ValueError("only an actionable proposal can receive feedback")
        action = proposal.get("action")
        if not isinstance(action, str) or not action.strip():
            raise ValueError("proposal must include a non-empty action")
        if execution_confirmed is not True:
            raise ValueError("external execution must be explicitly confirmed")
        if not isinstance(executed_action, str) or executed_action != action:
            raise ValueError("executed action does not match the proposal")
        context = proposal.get("context")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("proposal must include a non-empty context")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        evidence_ids = proposal.get("evidence_ids")
        if not isinstance(evidence_ids, (list, tuple)) or not evidence_ids:
            raise ValueError("proposal must include evidence_ids")
        if any(not isinstance(item, str) or not item.strip() for item in evidence_ids):
            raise ValueError("evidence_ids must contain non-empty strings")
        allowed = set(evidence_ids)
        if len(allowed) != len(evidence_ids):
            raise ValueError("proposal evidence_ids must be unique")
        if not isinstance(usefulness, Mapping) or not usefulness:
            raise ValueError("usefulness must be a non-empty mapping")
        if set(usefulness) - allowed:
            raise ValueError("feedback may only label evidence cited by the proposal")
        if any(not isinstance(key, str) or not key.strip() for key in usefulness):
            raise ValueError("usefulness keys must be non-empty fragment IDs")
        if any(not isinstance(value, bool) for value in usefulness.values()):
            raise ValueError("usefulness labels must be boolean")
        # Validate every referenced fragment before opening the atomic feedback batch.
        for fragment_id in usefulness:
            self.memory.get(fragment_id, record_access=False)
        scores, applied = self.memory.apply_context_feedback_batch(
            dict(usefulness), context=context, operation_id=operation_id,
            strength=self.strength,
        )
        return KnowledgeUseFeedbackResult(
            context=" ".join(context.casefold().split()),
            operation_id=operation_id,
            scores=tuple(sorted(scores.items())),
            applied=applied,
        )
