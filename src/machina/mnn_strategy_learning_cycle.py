"""Coordinated, explicit interface for MNN strategy proposal and learning.

The cycle joins contextual evidence review with two separate feedback channels:
organism-level reward learning and fragment-level usefulness attribution.
The channels remain separate so neither can silently substitute for the other.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .mnn_knowledge_use_feedback import MNNKnowledgeUseFeedback
from .mnn_strategy_decision_advisor import MNNStrategyDecisionAdvisor
from .mnn_strategy_feedback import MNNStrategyFeedbackAdapter, StrategyLearningResult
from .mnn_organism import MNNOrganism
from .mnn_strategy_context_memory import MNNStrategyContextMemory


class MNNStrategyLearningCycle:
    """Coordinate strategy proposals and separately attributed learning signals.

    This facade is intentionally not a transaction coordinator. Callers should
    persist/reconcile the two feedback channels independently: organism state
    and SQLite memory do not share a transaction boundary.
    """

    def __init__(
        self,
        advisor: MNNStrategyDecisionAdvisor,
        strategy_feedback: MNNStrategyFeedbackAdapter,
        knowledge_feedback: MNNKnowledgeUseFeedback,
    ) -> None:
        if not isinstance(advisor, MNNStrategyDecisionAdvisor):
            raise ValueError("advisor must be an MNNStrategyDecisionAdvisor")
        if not isinstance(strategy_feedback, MNNStrategyFeedbackAdapter):
            raise ValueError("strategy_feedback must be an MNNStrategyFeedbackAdapter")
        if not isinstance(knowledge_feedback, MNNKnowledgeUseFeedback):
            raise ValueError("knowledge_feedback must be an MNNKnowledgeUseFeedback")
        self.advisor = advisor
        self.strategy_feedback = strategy_feedback
        self.knowledge_feedback = knowledge_feedback

    def propose(
        self,
        context: str,
        campaign_ids: Sequence[str],
        *,
        min_conclusive_campaigns: int = 3,
        min_agreement_fraction: float = 0.75,
    ) -> dict[str, Any]:
        """Ask the evidence-gated advisor; proposals never execute themselves."""
        return self.advisor.propose(
            context,
            campaign_ids,
            min_conclusive_campaigns=min_conclusive_campaigns,
            min_agreement_fraction=min_agreement_fraction,
        )

    def learn_strategy_outcome(
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
        """Update organism learning only from the matching confirmed action."""
        return self.strategy_feedback.apply(
            organism,
            proposal,
            execution_confirmed=execution_confirmed,
            executed_action=executed_action,
            observed_reward=observed_reward,
            inputs=inputs,
            novelty=novelty,
            uncertainty=uncertainty,
            effort=effort,
            progress=progress,
            risk=risk,
        )

    def learn_evidence_use(
        self,
        proposal: Mapping[str, object],
        usefulness: Mapping[str, bool],
        *,
        execution_confirmed: bool,
        executed_action: str,
        operation_id: str,
    ):
        """Update only explicitly labelled, cited evidence relevance."""
        return self.knowledge_feedback.apply(
            proposal,
            usefulness,
            execution_confirmed=execution_confirmed,
            executed_action=executed_action,
            operation_id=operation_id,
        )
