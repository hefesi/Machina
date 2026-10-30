"""Context-separated, read-only memory of strategy campaign outcomes.

Campaigns are explicitly grouped by the caller. The evaluator still validates
that their stored contexts and action roles are compatible; this layer never
pools raw trials or changes an action policy.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .mnn_strategy_evaluation import MNNStrategyExperimentEvaluator


class MNNStrategyContextMemory:
    """Build context-specific strategy profiles from named experiment campaigns."""

    def __init__(self, evaluator: MNNStrategyExperimentEvaluator) -> None:
        if not isinstance(evaluator, MNNStrategyExperimentEvaluator):
            raise ValueError("evaluator must be an MNNStrategyExperimentEvaluator")
        self.evaluator = evaluator

    @staticmethod
    def _normalize_context(value: str) -> str:
        return " ".join(value.casefold().split())

    def review(
        self,
        context_campaigns: Mapping[str, Sequence[str]],
        *,
        min_conclusive_campaigns: int = 3,
        min_agreement_fraction: float = 0.75,
    ) -> dict[str, Any]:
        """Review independent campaign sequences without mixing contexts.

        Campaign order inside each sequence is retained for descriptive
        transition reporting; it is supplied explicitly by the caller and is
        not inferred from timestamps.
        """
        if not isinstance(context_campaigns, Mapping) or not context_campaigns:
            raise ValueError("context_campaigns must be a non-empty mapping")

        profiles: dict[str, dict[str, Any]] = {}
        normalized_contexts: set[str] = set()
        all_campaign_ids: set[str] = set()
        for context, campaign_ids in context_campaigns.items():
            if not isinstance(context, str) or not context.strip():
                raise ValueError("context names must be non-empty strings")
            normalized = self._normalize_context(context)
            if normalized in normalized_contexts:
                raise ValueError("context names must be unique after normalization")
            normalized_contexts.add(normalized)
            if isinstance(campaign_ids, (str, bytes)) or not isinstance(campaign_ids, Sequence):
                raise ValueError("each context must map to a sequence of campaign IDs")
            ids = []
            for campaign_id in campaign_ids:
                if not isinstance(campaign_id, str) or not campaign_id.strip():
                    raise ValueError("campaign IDs must be non-empty strings")
                ids.append(campaign_id.strip())
            if not ids or len(set(ids)) != len(ids):
                raise ValueError("each context requires unique campaign IDs")
            overlap = all_campaign_ids.intersection(ids)
            if overlap:
                raise ValueError("a campaign cannot belong to more than one context")
            all_campaign_ids.update(ids)

            aggregate = self.evaluator.evaluate_across_campaigns(
                ids,
                min_conclusive_campaigns=min_conclusive_campaigns,
                min_agreement_fraction=min_agreement_fraction,
            )
            observed = aggregate.get("context")
            context_matches = observed == normalized
            if aggregate.get("status") not in {"abstain"} and not context_matches:
                aggregate = {
                    **aggregate,
                    "status": "abstain",
                    "reason": "requested_context_does_not_match_stored_context",
                    "requested_context": normalized,
                    "observed_context": observed,
                }
            campaign_results = aggregate.get("campaign_results", [])
            sequence = [
                {
                    "campaign_id": result.get("campaign_id"),
                    "status": result.get("status"),
                    "reason": result.get("reason"),
                }
                for result in campaign_results
            ]
            conclusive_statuses = [
                item["status"] for item in sequence
                if item["status"] in {"candidate_better", "current_better"}
            ]
            transitions = [
                {"from": previous, "to": current, "between_campaigns": index}
                for index, (previous, current) in enumerate(
                    zip(conclusive_statuses, conclusive_statuses[1:]), start=1
                )
                if previous != current
            ]
            profiles[normalized] = {
                "requested_context": context,
                "normalized_context": normalized,
                "aggregate": aggregate,
                "campaign_sequence": sequence,
                "observed_advantage_transitions": transitions,
                "context_match": context_matches,
                "evidence_ids": sorted({
                    evidence_id
                    for result in campaign_results
                    for action_ids in result.get("evidence_ids", {}).values()
                    for evidence_id in action_ids
                }),
            }

        return {
            "status": "reviewed",
            "profiles": profiles,
            "context_count": len(profiles),
            "campaign_count": len(all_campaign_ids),
            "contexts_kept_separate": True,
            "raw_trials_pooled": False,
            "policy_changed": False,
            "causal_claim": False,
            "statistical_significance_claim": False,
            "method": "context-separated-independent-campaign-review",
        }
