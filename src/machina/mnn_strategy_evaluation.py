"""Conservative, read-only evaluation of repeated strategy experiments.

The evaluator compares observed rewards within an explicitly named campaign.
It reports empirical associations, not causal effects, and never changes policy.
"""
from __future__ import annotations

import math
from typing import Any

from .fragment_memory import FragmentMemory


class MNNStrategyExperimentEvaluator:
    """Compare current and candidate actions using append-only trial records."""

    def __init__(
        self,
        memory: FragmentMemory,
        actions: tuple[str, ...] | list[str],
        *,
        min_samples_per_action: int = 3,
        min_reward_margin: float = 0.1,
    ) -> None:
        if not isinstance(memory, FragmentMemory):
            raise ValueError("memory must be a FragmentMemory")
        names = tuple(actions)
        if len(names) < 2 or any(not isinstance(a, str) or not a.strip() for a in names):
            raise ValueError("at least two non-empty action names are required")
        if len(set(names)) != len(names):
            raise ValueError("action names must be unique")
        if isinstance(min_samples_per_action, bool) or not isinstance(min_samples_per_action, int) or min_samples_per_action < 1:
            raise ValueError("min_samples_per_action must be a positive integer")
        if isinstance(min_reward_margin, bool) or not isinstance(min_reward_margin, (int, float)) or not math.isfinite(min_reward_margin) or min_reward_margin < 0:
            raise ValueError("min_reward_margin must be a finite non-negative number")
        self.memory = memory
        self.actions = names
        self.min_samples_per_action = min_samples_per_action
        self.min_reward_margin = float(min_reward_margin)

    def evaluate(self, campaign_id: str) -> dict[str, Any]:
        """Evaluate one campaign; abstain if role or sample evidence is ambiguous."""
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            raise ValueError("campaign_id must be a non-empty string")
        campaign_id = campaign_id.strip()
        archive = [
            item for item in self.memory.archive()
            if item.kind == "strategy-experiment"
        ]
        proposals = {
            item.metadata.get("experiment_id"): item
            for item in archive
            if item.metadata.get("event") == "proposal"
            and item.metadata.get("campaign_id", item.metadata.get("experiment_id")) == campaign_id
        }
        if not proposals:
            return self._result("abstain", campaign_id, reason="no_campaign_proposals")

        roles: set[tuple[str, str]] = set()
        contexts: set[str] = set()
        for proposal in proposals.values():
            current = proposal.metadata.get("current_action")
            candidate = proposal.metadata.get("candidate_action")
            if candidate is None:
                candidate = proposal.metadata.get("planned_action")
            context = proposal.metadata.get("context")
            if isinstance(context, str) and context.strip():
                contexts.add(" ".join(context.casefold().split()))
            if current not in self.actions or candidate not in self.actions or current == candidate:
                continue
            roles.add((current, candidate))
        if len(contexts) != 1:
            return self._result(
                "abstain", campaign_id, reason="inconsistent_campaign_context",
                proposal_ids=[item.id for item in proposals.values()],
                context_count=len(contexts),
            )
        if len(roles) != 1:
            return self._result(
                "abstain", campaign_id, reason="ambiguous_action_roles",
                proposal_ids=[item.id for item in proposals.values()],
            )
        current_action, candidate_action = next(iter(roles))
        outcomes_by_action: dict[str, list[tuple[float, str]]] = {
            current_action: [], candidate_action: []
        }
        for outcome in archive:
            metadata = outcome.metadata
            if metadata.get("event") != "outcome":
                continue
            experiment_id = metadata.get("experiment_id")
            proposal = proposals.get(experiment_id)
            if proposal is None or metadata.get("proposal_fragment_id") != proposal.id:
                continue
            action = metadata.get("tested_action")
            reward = metadata.get("observed_reward")
            if action not in outcomes_by_action:
                continue
            if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
                continue
            outcomes_by_action[action].append((float(reward), outcome.id))

        current = outcomes_by_action[current_action]
        candidate = outcomes_by_action[candidate_action]
        means = {
            current_action: (sum(value for value, _ in current) / len(current)) if current else None,
            candidate_action: (sum(value for value, _ in candidate) / len(candidate)) if candidate else None,
        }
        evidence_ids = {
            current_action: [fragment_id for _, fragment_id in current],
            candidate_action: [fragment_id for _, fragment_id in candidate],
        }
        common = {
            "current_action": current_action,
            "candidate_action": candidate_action,
            "sample_counts": {current_action: len(current), candidate_action: len(candidate)},
            "mean_rewards": means,
            "evidence_ids": evidence_ids,
            "min_samples_per_action": self.min_samples_per_action,
            "min_reward_margin": self.min_reward_margin,
            "method": "unweighted-empirical-mean-with-minimum-samples-and-margin",
            "causal_claim": False,
        }
        if min(len(current), len(candidate)) < self.min_samples_per_action:
            return self._result("inconclusive", campaign_id, reason="insufficient_samples", **common)
        difference = means[candidate_action] - means[current_action]
        if difference >= self.min_reward_margin and difference > 0:
            status = "candidate_better"
            reason = "candidate_mean_exceeds_current_by_required_margin"
        elif difference <= -self.min_reward_margin and difference < 0:
            status = "current_better"
            reason = "current_mean_exceeds_candidate_by_required_margin"
        else:
            status = "inconclusive"
            reason = "reward_difference_below_required_margin"
        return self._result(status, campaign_id, reason=reason, reward_difference=difference, **common)

    @staticmethod
    def _result(status: str, campaign_id: str, *, reason: str, **details: Any) -> dict[str, Any]:
        return {"status": status, "campaign_id": campaign_id, "reason": reason, **details}
