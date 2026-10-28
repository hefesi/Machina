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
        noise_guard_multiplier: float = 1.0,
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
        if isinstance(noise_guard_multiplier, bool) or not isinstance(noise_guard_multiplier, (int, float)) or not math.isfinite(noise_guard_multiplier) or noise_guard_multiplier < 0:
            raise ValueError("noise_guard_multiplier must be a finite non-negative number")
        self.memory = memory
        self.actions = names
        self.min_samples_per_action = min_samples_per_action
        self.min_reward_margin = float(min_reward_margin)
        self.noise_guard_multiplier = float(noise_guard_multiplier)

    def evaluate(self, campaign_id: str) -> dict[str, Any]:
        """Evaluate one campaign; abstain if role, context, or evidence is ambiguous."""
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

        def summarize(samples: list[tuple[float, str]]) -> tuple[float | None, float | None]:
            values = [value for value, _ in samples]
            if not values:
                return None, None
            mean = sum(values) / len(values)
            if len(values) < 2:
                return mean, None
            # Sample variance (Bessel-corrected); clamp tiny negative roundoff.
            variance = max(0.0, sum((value - mean) ** 2 for value in values) / (len(values) - 1))
            return mean, variance

        current_mean, current_variance = summarize(current)
        candidate_mean, candidate_variance = summarize(candidate)
        means = {current_action: current_mean, candidate_action: candidate_mean}
        variances = {current_action: current_variance, candidate_action: candidate_variance}
        stddevs = {
            action: math.sqrt(variance) if variance is not None else None
            for action, variance in variances.items()
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
            "sample_variances": variances,
            "sample_standard_deviations": stddevs,
            "evidence_ids": evidence_ids,
            "min_samples_per_action": self.min_samples_per_action,
            "min_reward_margin": self.min_reward_margin,
            "noise_guard_multiplier": self.noise_guard_multiplier,
            "method": "empirical-mean-margin-with-variance-based-noise-guard",
            "causal_claim": False,
            "statistical_significance_claim": False,
        }
        if min(len(current), len(candidate)) < self.min_samples_per_action:
            return self._result("inconclusive", campaign_id, reason="insufficient_samples", **common)
        # A sample variance cannot be estimated from a single observation. Do
        # not treat missing variance as zero noise, even if configured minimum is 1.
        if current_variance is None or candidate_variance is None:
            return self._result("inconclusive", campaign_id, reason="insufficient_samples_for_variability", **common)

        difference = candidate_mean - current_mean
        standard_error = math.sqrt(
            current_variance / len(current) + candidate_variance / len(candidate)
        )
        noise_threshold = self.noise_guard_multiplier * standard_error
        common.update({
            "reward_difference": difference,
            "difference_standard_error": standard_error,
            "noise_threshold": noise_threshold,
        })
        if difference >= self.min_reward_margin and difference > noise_threshold:
            status = "candidate_better"
            reason = "candidate_mean_exceeds_margin_and_noise_guard"
        elif difference <= -self.min_reward_margin and -difference > noise_threshold:
            status = "current_better"
            reason = "current_mean_exceeds_margin_and_noise_guard"
        elif abs(difference) < self.min_reward_margin:
            status = "inconclusive"
            reason = "reward_difference_below_required_margin"
        else:
            status = "inconclusive"
            reason = "reward_difference_not_larger_than_noise_guard"
        return self._result(status, campaign_id, reason=reason, **common)

    def evaluate_across_campaigns(
        self,
        campaign_ids: list[str] | tuple[str, ...],
        *,
        min_conclusive_campaigns: int = 3,
        min_agreement_fraction: float = 0.75,
    ) -> dict[str, Any]:
        """Review whether campaign-level outcomes agree, without pooling trials.

        All campaigns must describe the same normalized context and the same
        current/candidate action roles. Inconclusive campaigns are reported but
        excluded from the agreement denominator.
        """
        if isinstance(campaign_ids, (str, bytes)) or not isinstance(campaign_ids, (list, tuple)):
            raise ValueError("campaign_ids must be a list or tuple of campaign IDs")
        normalized_ids = []
        for campaign_id in campaign_ids:
            if not isinstance(campaign_id, str) or not campaign_id.strip():
                raise ValueError("campaign IDs must be non-empty strings")
            normalized_ids.append(campaign_id.strip())
        if not normalized_ids:
            raise ValueError("at least one campaign ID is required")
        if len(set(normalized_ids)) != len(normalized_ids):
            raise ValueError("campaign IDs must be unique")
        if (isinstance(min_conclusive_campaigns, bool)
                or not isinstance(min_conclusive_campaigns, int)
                or min_conclusive_campaigns < 2):
            raise ValueError("min_conclusive_campaigns must be an integer of at least 2")
        if (isinstance(min_agreement_fraction, bool)
                or not isinstance(min_agreement_fraction, (int, float))
                or not math.isfinite(min_agreement_fraction)
                or not 0.5 < min_agreement_fraction <= 1.0):
            raise ValueError("min_agreement_fraction must be greater than 0.5 and at most 1")

        archive = [
            item for item in self.memory.archive()
            if item.kind == "strategy-experiment" and item.metadata.get("event") == "proposal"
        ]
        expected_context = None
        expected_roles = None
        for campaign_id in normalized_ids:
            proposals = [
                item for item in archive
                if item.metadata.get("campaign_id", item.metadata.get("experiment_id")) == campaign_id
            ]
            if not proposals:
                return self._result(
                    "abstain", campaign_id, reason="no_campaign_proposals",
                    requested_campaign_ids=normalized_ids,
                )
            contexts = {
                " ".join(value.casefold().split())
                for item in proposals
                if isinstance((value := item.metadata.get("context")), str) and value.strip()
            }
            roles = set()
            for item in proposals:
                current = item.metadata.get("current_action")
                candidate = item.metadata.get("candidate_action")
                if candidate is None:
                    candidate = item.metadata.get("planned_action")
                if current in self.actions and candidate in self.actions and current != candidate:
                    roles.add((current, candidate))
            if len(contexts) != 1:
                return self._result(
                    "abstain", "cross-campaign", reason="inconsistent_campaign_context",
                    campaign_id=campaign_id, context_count=len(contexts),
                )
            if len(roles) != 1:
                return self._result(
                    "abstain", "cross-campaign", reason="ambiguous_action_roles",
                    campaign_id=campaign_id,
                )
            context = next(iter(contexts))
            role_pair = next(iter(roles))
            if expected_context is None:
                expected_context, expected_roles = context, role_pair
            elif context != expected_context:
                return self._result(
                    "abstain", "cross-campaign", reason="incompatible_campaign_contexts",
                    campaign_id=campaign_id, expected_context=expected_context,
                    observed_context=context,
                )
            elif role_pair != expected_roles:
                return self._result(
                    "abstain", "cross-campaign", reason="incompatible_action_roles",
                    campaign_id=campaign_id, expected_action_roles=expected_roles,
                    observed_action_roles=role_pair,
                )

        campaign_results = [self.evaluate(campaign_id) for campaign_id in normalized_ids]
        conclusive = [
            result for result in campaign_results
            if result.get("status") in {"candidate_better", "current_better"}
        ]
        counts = {
            "candidate_better": sum(result["status"] == "candidate_better" for result in conclusive),
            "current_better": sum(result["status"] == "current_better" for result in conclusive),
            "inconclusive": sum(result["status"] == "inconclusive" for result in campaign_results),
        }
        common = {
            "campaign_ids": normalized_ids,
            "campaign_results": campaign_results,
            "conclusive_campaign_count": len(conclusive),
            "status_counts": counts,
            "min_conclusive_campaigns": min_conclusive_campaigns,
            "min_agreement_fraction": float(min_agreement_fraction),
            "agreement_fraction": (
                max(counts["candidate_better"], counts["current_better"]) / len(conclusive)
                if conclusive else None
            ),
            "current_action": expected_roles[0],
            "candidate_action": expected_roles[1],
            "context": expected_context,
            "method": "agreement-of-independent-campaign-level-evaluations",
            "causal_claim": False,
            "statistical_significance_claim": False,
            "raw_trials_pooled": False,
        }
        if len(conclusive) < min_conclusive_campaigns:
            return self._result(
                "inconclusive", "cross-campaign", reason="insufficient_conclusive_campaigns",
                **common,
            )
        agreement = common["agreement_fraction"]
        if agreement < min_agreement_fraction:
            return self._result(
                "mixed_results", "cross-campaign", reason="campaign_results_do_not_agree",
                **common,
            )
        if counts["candidate_better"] > counts["current_better"]:
            return self._result(
                "consistent_candidate_advantage", "cross-campaign",
                reason="candidate_advantage_repeats_across_campaigns", **common,
            )
        return self._result(
            "consistent_current_advantage", "cross-campaign",
            reason="current_action_advantage_repeats_across_campaigns", **common,
        )

    @staticmethod
    def _result(status: str, campaign_id: str, *, reason: str, **details: Any) -> dict[str, Any]:
        return {"status": status, "campaign_id": campaign_id, "reason": reason, **details}

    def evaluate_over_time(self, campaign_id: str, *, window_size: int = 3) -> dict[str, Any]:
        """Compare candidate advantage in early versus late observations.

        Outcomes are ordered by their persisted creation time. This is a
        descriptive drift check, not a causal or statistical significance test.
        """
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            raise ValueError("campaign_id must be a non-empty string")
        if isinstance(window_size, bool) or not isinstance(window_size, int) or window_size < 2:
            raise ValueError("window_size must be an integer of at least 2")
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

        contexts = {
            " ".join(item.metadata.get("context", "").casefold().split())
            for item in proposals.values()
            if isinstance(item.metadata.get("context"), str) and item.metadata.get("context", "").strip()
        }
        roles = set()
        for proposal in proposals.values():
            current = proposal.metadata.get("current_action")
            candidate = proposal.metadata.get("candidate_action") or proposal.metadata.get("planned_action")
            if current in self.actions and candidate in self.actions and current != candidate:
                roles.add((current, candidate))
        if len(contexts) != 1:
            return self._result("abstain", campaign_id, reason="inconsistent_campaign_context",
                                context_count=len(contexts))
        if len(roles) != 1:
            return self._result("abstain", campaign_id, reason="ambiguous_action_roles")
        current_action, candidate_action = next(iter(roles))
        outcomes: dict[str, list[tuple[str, float, str]]] = {
            current_action: [], candidate_action: []
        }
        for item in archive:
            metadata = item.metadata
            if metadata.get("event") != "outcome":
                continue
            proposal = proposals.get(metadata.get("experiment_id"))
            if proposal is None or metadata.get("proposal_fragment_id") != proposal.id:
                continue
            action = metadata.get("tested_action")
            reward = metadata.get("observed_reward")
            if action not in outcomes or isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
                continue
            outcomes[action].append((item.created_at, float(reward), item.id))

        required = window_size * 2
        counts = {action: len(items) for action, items in outcomes.items()}
        if any(count < required for count in counts.values()):
            return self._result(
                "inconclusive", campaign_id, reason="insufficient_temporal_samples",
                current_action=current_action, candidate_action=candidate_action,
                sample_counts=counts, window_size=window_size,
                required_per_action=required,
            )

        windows: dict[str, dict[str, Any]] = {}
        for action, samples in outcomes.items():
            samples.sort(key=lambda entry: (entry[0], entry[2]))
            early = samples[:window_size]
            late = samples[-window_size:]
            windows[action] = {
                "early_mean": sum(value for _, value, _ in early) / window_size,
                "late_mean": sum(value for _, value, _ in late) / window_size,
                "early_evidence_ids": [fragment_id for _, _, fragment_id in early],
                "late_evidence_ids": [fragment_id for _, _, fragment_id in late],
            }

        early_advantage = windows[candidate_action]["early_mean"] - windows[current_action]["early_mean"]
        late_advantage = windows[candidate_action]["late_mean"] - windows[current_action]["late_mean"]
        early_positive = early_advantage >= self.min_reward_margin
        late_positive = late_advantage >= self.min_reward_margin
        if early_positive and late_positive:
            status, reason = "advantage_persisted", "candidate_advantage_meets_margin_in_both_windows"
        elif not early_positive and late_positive:
            status, reason = "advantage_emerged", "candidate_advantage_meets_margin_only_in_late_window"
        elif early_positive and late_advantage <= -self.min_reward_margin:
            status, reason = "advantage_reversed", "candidate_advantage_reversed_beyond_margin"
        else:
            status, reason = "no_clear_change", "advantage_not_consistent_across_windows"
        return self._result(
            status, campaign_id, reason=reason,
            current_action=current_action, candidate_action=candidate_action,
            sample_counts=counts, window_size=window_size,
            early_advantage=early_advantage, late_advantage=late_advantage,
            change_in_advantage=late_advantage - early_advantage,
            action_windows=windows, causal_claim=False,
            statistical_significance_claim=False,
            method="chronological-early-versus-late-window-mean-comparison",
        )
