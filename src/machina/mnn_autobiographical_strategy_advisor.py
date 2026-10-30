"""Context-matched strategy review from replayed autobiographical events.

Only explicitly confirmed strategy outcomes are considered. The advisor is
read-only and returns a candidate for validation; it never changes policy.
"""
from __future__ import annotations

from collections import defaultdict
import math
from typing import Any

from .mnn_autobiographical_recall import MNNAutobiographicalRecall


class MNNAutobiographicalStrategyAdvisor:
    """Compare action outcomes recorded in distinct cognitive cycles."""

    def __init__(
        self,
        recall: MNNAutobiographicalRecall,
        actions: tuple[str, ...] | list[str],
        *,
        min_cycles_per_action: int = 3,
        min_reward_margin: float = 0.1,
        noise_guard_multiplier: float = 1.0,
        recall_limit: int = 500,
    ) -> None:
        if not isinstance(recall, MNNAutobiographicalRecall):
            raise TypeError("recall must be an MNNAutobiographicalRecall")
        names = tuple(actions)
        if len(names) < 2 or any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("at least two non-empty action names are required")
        names = tuple(name.strip() for name in names)
        if len(set(names)) != len(names):
            raise ValueError("action names must be unique")
        if (isinstance(min_cycles_per_action, bool) or not isinstance(min_cycles_per_action, int)
                or min_cycles_per_action < 2):
            raise ValueError("min_cycles_per_action must be an integer of at least 2")
        for name, value in (
            ("min_reward_margin", min_reward_margin),
            ("noise_guard_multiplier", noise_guard_multiplier),
        ):
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or value < 0):
                raise ValueError(f"{name} must be finite and non-negative")
        if (isinstance(recall_limit, bool) or not isinstance(recall_limit, int)
                or recall_limit < 1):
            raise ValueError("recall_limit must be a positive integer")
        self.recall = recall
        self.actions = names
        self.min_cycles_per_action = min_cycles_per_action
        self.min_reward_margin = float(min_reward_margin)
        self.noise_guard_multiplier = float(noise_guard_multiplier)
        self.recall_limit = recall_limit

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())

    def review(self, context: str, *, current_action: str) -> dict[str, Any]:
        """Compare confirmed outcomes for one exact context; abstain on weak data."""
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        if current_action not in self.actions:
            raise ValueError("current_action must be one of the configured actions")
        normalized_context = self._normalize(context)
        episodes = self.recall.recall(
            normalized_context, limit=self.recall_limit, context=normalized_context
        )
        samples: dict[str, list[tuple[float, str, str, int]]] = {
            action: [] for action in self.actions
        }
        ignored = {
            "non_outcome_event": 0,
            "context_mismatch": 0,
            "unconfirmed_or_invalid_reward": 0,
            "unknown_action": 0,
        }
        for episode in episodes:
            if episode.event_type != "strategy.outcome.recorded":
                ignored["non_outcome_event"] += 1
                continue
            data = episode.artifact.get("data")
            if not isinstance(data, dict):
                ignored["unconfirmed_or_invalid_reward"] += 1
                continue
            event_context = data.get("context")
            if not isinstance(event_context, str) or self._normalize(event_context) != normalized_context:
                ignored["context_mismatch"] += 1
                continue
            if data.get("execution_confirmed") is not True:
                ignored["unconfirmed_or_invalid_reward"] += 1
                continue
            action = data.get("action")
            if action not in samples:
                ignored["unknown_action"] += 1
                continue
            reward = data.get("observed_reward")
            if (isinstance(reward, bool) or not isinstance(reward, (int, float))
                    or not math.isfinite(reward) or not 0.0 <= reward <= 1.0):
                ignored["unconfirmed_or_invalid_reward"] += 1
                continue
            samples[action].append((float(reward), episode.cycle_id, episode.event_id, episode.sequence))

        summaries: dict[str, dict[str, Any]] = {}
        for action, records in samples.items():
            values_by_cycle: dict[str, list[float]] = defaultdict(list)
            for reward, cycle_id, _event_id, _sequence in records:
                values_by_cycle[cycle_id].append(reward)
            cycles = sorted(values_by_cycle)
            # Give each cognitive cycle equal weight. Multiple outcomes within
            # one cycle are summarized before estimating across-cycle variance.
            cycle_means = [
                sum(values_by_cycle[cycle_id]) / len(values_by_cycle[cycle_id])
                for cycle_id in cycles
            ]
            mean = sum(cycle_means) / len(cycle_means) if cycle_means else None
            variance = (
                sum((value - mean) ** 2 for value in cycle_means) / (len(cycle_means) - 1)
                if len(cycle_means) >= 2 else None
            )
            summaries[action] = {
                "sample_count": len(cycle_means),
                "outcome_count": len(records),
                "distinct_cycle_count": len(cycles),
                "mean_observed_reward": mean,
                "sample_variance": variance,
                "event_ids": [record[2] for record in sorted(records, key=lambda item: item[3])],
                "cycle_ids": cycles,
            }

        insufficient = [
            action for action, summary in summaries.items()
            if summary["distinct_cycle_count"] < self.min_cycles_per_action
            or summary["sample_count"] < 2
            or summary["sample_variance"] is None
        ]
        common = {
            "context": normalized_context,
            "current_action": current_action,
            "action_summaries": summaries,
            "ignored_records": ignored,
            "min_cycles_per_action": self.min_cycles_per_action,
            "min_reward_margin": self.min_reward_margin,
            "noise_guard_multiplier": self.noise_guard_multiplier,
            "evidence_event_ids": sorted({
                event_id for summary in summaries.values()
                for event_id in summary["event_ids"]
            }),
            "policy_changed": False,
            "executed": False,
            "causal_claim": False,
            "statistical_significance_claim": False,
            "method": "exact-context-empirical-means-with-sample-variance-guard",
        }
        if insufficient:
            return {
                "status": "inconclusive",
                "reason": "insufficient_confirmed_outcomes_across_distinct_cycles",
                "insufficient_actions": insufficient,
                **common,
            }

        ranked = sorted(
            self.actions,
            key=lambda action: (-summaries[action]["mean_observed_reward"], self.actions.index(action)),
        )
        best = ranked[0]
        current = summaries[current_action]
        candidate = summaries[best]
        difference = candidate["mean_observed_reward"] - current["mean_observed_reward"]
        standard_error = math.sqrt(
            current["sample_variance"] / current["sample_count"]
            + candidate["sample_variance"] / candidate["sample_count"]
        )
        noise_threshold = self.noise_guard_multiplier * standard_error
        common.update({
            "best_observed_action": best,
            "observed_reward_difference": difference,
            "difference_standard_error": standard_error,
            "noise_threshold": noise_threshold,
        })
        if best == current_action or difference < self.min_reward_margin or difference <= noise_threshold:
            return {
                "status": "maintain",
                "reason": "no_alternative_clears_margin_and_variability_guard",
                **common,
            }
        return {
            "status": "candidate",
            "reason": "alternative_repeatedly_outperformed_current_action_in_matching_context",
            "candidate_action": best,
            "interpretation": "Candidate for controlled validation; not a causal conclusion or automatic switch.",
            **common,
        }
