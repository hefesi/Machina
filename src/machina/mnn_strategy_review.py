"""Evidence-gated review of alternative actions after contextual reward drift."""
from __future__ import annotations

import math

from .mnn_reward_drift import MNNRewardDriftDetector


class MNNStrategyReviewer:
    """Propose, but never execute, a strategy alternative using drift evidence.

    A proposal requires a detected shift, comparable samples for every action in
    both windows, and a minimum recent-reward margin over the current action.
    The result is an observational suggestion, not a causal or safety guarantee.
    """

    def __init__(
        self,
        detector: MNNRewardDriftDetector,
        actions: tuple[str, ...] | list[str],
        *,
        min_recent_samples: int = 2,
        min_reward_margin: float = 0.1,
    ) -> None:
        if not isinstance(detector, MNNRewardDriftDetector):
            raise ValueError("detector must be an MNNRewardDriftDetector")
        names = tuple(actions)
        if len(names) < 2 or any(not isinstance(a, str) or not a.strip() for a in names):
            raise ValueError("at least two non-empty action names are required")
        if len(set(names)) != len(names):
            raise ValueError("action names must be unique")
        if (isinstance(min_recent_samples, bool) or not isinstance(min_recent_samples, int)
                or min_recent_samples < 1):
            raise ValueError("min_recent_samples must be a positive integer")
        if (isinstance(min_reward_margin, bool)
                or not isinstance(min_reward_margin, (int, float))
                or not math.isfinite(min_reward_margin) or min_reward_margin < 0):
            raise ValueError("min_reward_margin must be finite and non-negative")
        self.detector = detector
        self.actions = names
        self.min_recent_samples = min_recent_samples
        self.min_reward_margin = float(min_reward_margin)

    def review(self, context: str, *, current_action: str) -> dict:
        """Return a candidate recommendation or abstain, preserving the evidence."""
        if not isinstance(current_action, str) or current_action not in self.actions:
            raise ValueError("current_action must be one of the configured actions")
        report = self.detector.detect(context)
        if report["status"] != "detected":
            return {
                "status": "abstain",
                "reason": "no_confirmed_reward_drift",
                "current_action": current_action,
                "drift_report": report,
            }
        comparisons = report.get("comparisons", {})
        estimates = {}
        evidence = {}
        for action in self.actions:
            item = comparisons.get(action, {})
            if (item.get("status") not in {"shift_detected", "within_threshold"}
                    or item.get("recent_samples", 0) < self.min_recent_samples
                    or not isinstance(item.get("recent_mean_reward"), (int, float))
                    or not math.isfinite(item["recent_mean_reward"])):
                return {
                    "status": "abstain",
                    "reason": "insufficient_comparable_recent_action_evidence",
                    "current_action": current_action,
                    "drift_report": report,
                    "missing_or_insufficient_actions": [
                        name for name in self.actions
                        if (comparisons.get(name, {}).get("status") not in {"shift_detected", "within_threshold"}
                            or comparisons.get(name, {}).get("recent_samples", 0) < self.min_recent_samples)
                    ],
                }
            estimates[action] = float(item["recent_mean_reward"])
            evidence[action] = {
                "previous_samples": item["previous_samples"],
                "recent_samples": item["recent_samples"],
                "previous_mean_reward": item["previous_mean_reward"],
                "recent_mean_reward": item["recent_mean_reward"],
                "previous_evidence_ids": item.get("previous_evidence_ids", []),
                "recent_evidence_ids": item.get("recent_evidence_ids", []),
            }
        ranked = sorted(self.actions, key=lambda name: (-estimates[name], self.actions.index(name)))
        best = ranked[0]
        margin = estimates[best] - estimates[current_action]
        if best == current_action or margin < self.min_reward_margin:
            return {
                "status": "maintain",
                "reason": "no_alternative_meets_minimum_recent_reward_margin",
                "current_action": current_action,
                "estimated_recent_rewards": estimates,
                "improvement_over_current": margin,
                "minimum_reward_margin": self.min_reward_margin,
                "evidence": evidence,
                "drift_report": report,
            }
        return {
            "status": "candidate",
            "reason": "alternative_has_sufficient_recent_observed_reward_margin",
            "current_action": current_action,
            "candidate_action": best,
            "estimated_recent_rewards": estimates,
            "improvement_over_current": margin,
            "minimum_reward_margin": self.min_reward_margin,
            "evidence": evidence,
            "drift_report": report,
            "interpretation": "Candidate for controlled validation; not an automatic policy switch.",
        }
