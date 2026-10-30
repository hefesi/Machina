"""Explicit bridge from externally confirmed strategy outcomes to MNN learning.

A recommendation is not an experience. This adapter accepts feedback only
when the caller confirms that the proposed action was executed and supplies
its observed reward. It then routes a bounded event through MNNOrganism.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .chemical_signaling import ChemicalEvent
from .mnn_organism import MNNOrganism, OrganismStep


@dataclass(frozen=True)
class StrategyFeedback:
    """Auditable learning event derived from one externally confirmed action."""

    context: str
    action: str
    evidence_ids: tuple[str, ...]
    event: ChemicalEvent


@dataclass(frozen=True)
class StrategyLearningResult:
    """Result of applying one confirmed strategy outcome to the organism."""

    feedback: StrategyFeedback
    organism_step: OrganismStep


class MNNStrategyFeedbackAdapter:
    """Convert confirmed strategy outcomes into explicit organism learning."""

    @staticmethod
    def _unit_interval(name: str, value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be within [0, 1]")
        return float(value)

    def apply(
        self,
        organism: MNNOrganism,
        proposal: Mapping[str, object],
        *,
        execution_confirmed: bool,
        executed_action: str,
        observed_reward: float,
        inputs: Mapping[str, float] | None = None,
        novelty: float = 0.0,
        uncertainty: float = 0.0,
        effort: float = 0.0,
        progress: float = 0.0,
        risk: float = 0.0,
    ) -> StrategyLearningResult:
        """Advance the organism using reward only after explicit execution confirmation.

        Reward and contextual features use the existing ChemicalEvent [0, 1]
        scale. Mapping arbitrary task rewards to this scale is the caller's job.
        """
        if not isinstance(organism, MNNOrganism):
            raise ValueError("organism must be an MNNOrganism")
        if not isinstance(proposal, Mapping):
            raise ValueError("proposal must be a mapping")
        if proposal.get("status") != "proposed" or not proposal.get("action"):
            raise ValueError("only an actionable proposal can receive feedback")
        if execution_confirmed is not True:
            raise ValueError("external execution must be explicitly confirmed")
        action = proposal.get("action")
        if not isinstance(action, str) or not isinstance(executed_action, str):
            raise ValueError("proposal and executed action must be strings")
        if action != executed_action:
            raise ValueError("executed action does not match the proposed action")
        context = proposal.get("context")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("proposal must include a non-empty context")
        evidence_ids = proposal.get("evidence_ids", ())
        if not isinstance(evidence_ids, (list, tuple)) or any(
            not isinstance(item, str) or not item for item in evidence_ids
        ):
            raise ValueError("proposal evidence_ids must be a sequence of non-empty IDs")

        event = ChemicalEvent(
            reward=self._unit_interval("observed_reward", observed_reward),
            novelty=self._unit_interval("novelty", novelty),
            uncertainty=self._unit_interval("uncertainty", uncertainty),
            effort=self._unit_interval("effort", effort),
            progress=self._unit_interval("progress", progress),
            risk=self._unit_interval("risk", risk),
        )
        feedback = StrategyFeedback(
            context=" ".join(context.casefold().split()),
            action=action,
            evidence_ids=tuple(evidence_ids),
            event=event,
        )
        step = organism.step(inputs=inputs, event=event)
        return StrategyLearningResult(feedback=feedback, organism_step=step)
