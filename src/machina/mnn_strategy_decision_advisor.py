"""Evidence-gated bridge from contextual strategy memory to action proposals.

This component is advisory only: it never executes actions, updates policies,
or treats observational campaign results as causal proof.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .mnn_strategy_context_memory import MNNStrategyContextMemory


class MNNStrategyDecisionAdvisor:
    """Propose an action only when independent campaigns agree in context."""

    def __init__(self, context_memory: MNNStrategyContextMemory) -> None:
        if not isinstance(context_memory, MNNStrategyContextMemory):
            raise ValueError("context_memory must be an MNNStrategyContextMemory")
        self.context_memory = context_memory

    def propose(
        self,
        context: str,
        campaign_ids: Sequence[str],
        *,
        min_conclusive_campaigns: int = 3,
        min_agreement_fraction: float = 0.75,
    ) -> dict[str, Any]:
        """Return a traceable proposal or abstain; never perform the action."""
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        if isinstance(campaign_ids, (str, bytes)) or not isinstance(campaign_ids, Sequence):
            raise ValueError("campaign_ids must be a sequence of campaign IDs")
        ids = []
        for campaign_id in campaign_ids:
            if not isinstance(campaign_id, str) or not campaign_id.strip():
                raise ValueError("campaign IDs must be non-empty strings")
            ids.append(campaign_id.strip())
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("campaign_ids must be non-empty and unique")

        review = self.context_memory.review(
            {context: ids},
            min_conclusive_campaigns=min_conclusive_campaigns,
            min_agreement_fraction=min_agreement_fraction,
        )
        profile = review["profiles"][" ".join(context.casefold().split())]
        aggregate = profile["aggregate"]
        campaign_status = aggregate.get("status")

        if campaign_status == "consistent_candidate_advantage":
            action, status = aggregate["candidate_action"], "proposed"
            reason = "candidate_advantage_repeated_in_context"
        elif campaign_status == "consistent_current_advantage":
            action, status = aggregate["current_action"], "proposed"
            reason = "current_advantage_repeated_in_context"
        else:
            action, status = None, "abstain"
            reason = aggregate.get("reason", "no_repeated_contextual_advantage")

        evidence_ids = sorted({
            evidence_id
            for result in aggregate.get("campaign_results", [])
            for action_evidence in result.get("evidence_ids", {}).values()
            for evidence_id in action_evidence
        })
        return {
            "status": status,
            "reason": reason,
            "action": action,
            "context": " ".join(context.casefold().split()),
            "campaign_ids": ids,
            "campaign_review_status": campaign_status,
            "conclusive_campaign_count": aggregate.get("conclusive_campaign_count", 0),
            "agreement_fraction": aggregate.get("agreement_fraction"),
            "evidence_ids": evidence_ids,
            "executed": False,
            "policy_changed": False,
            "requires_external_execution": True,
            "raw_trials_pooled": False,
            "causal_claim": False,
            "statistical_significance_claim": False,
            "method": "contextual-independent-campaign-advisory",
        }
