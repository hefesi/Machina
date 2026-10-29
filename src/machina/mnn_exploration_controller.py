"""Bounded, auditable exploration adjustment driven by reward-drift reviews.

The controller never chooses an action or updates learned values. Call
observe_review with a review-cycle result, then pass epsilon_for to the agent.
Repeated evidence cannot continually extend the exploration window.
"""
from __future__ import annotations

import math
from collections.abc import Mapping


class MNNBoundedExplorationController:
    """Temporarily raise epsilon after new, detected reward-drift evidence."""

    def __init__(self, *, base_epsilon: float = 0.05, elevated_epsilon: float = 0.25, duration_decisions: int = 5) -> None:
        for name, value in (("base_epsilon", base_epsilon), ("elevated_epsilon", elevated_epsilon)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and in [0, 1]")
        if elevated_epsilon < base_epsilon:
            raise ValueError("elevated_epsilon must be greater than or equal to base_epsilon")
        if isinstance(duration_decisions, bool) or not isinstance(duration_decisions, int) or duration_decisions < 1:
            raise ValueError("duration_decisions must be a positive integer")
        self.base_epsilon = float(base_epsilon)
        self.elevated_epsilon = float(elevated_epsilon)
        self.duration_decisions = duration_decisions
        self.active_until_decision: int | None = None
        self._seen_evidence_fingerprints: set[str] = set()
        self.last_activation: dict | None = None

    @staticmethod
    def _decision_index(value: int) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError("decision_index must be a non-negative integer")
        return value

    def observe_review(self, review: Mapping, *, decision_index: int) -> dict:
        """Consume one review result; activate only for novel detected evidence."""
        decision_index = self._decision_index(decision_index)
        if not isinstance(review, Mapping):
            raise ValueError("review must be a mapping")
        recommendation = review.get("recommendation")
        if not isinstance(recommendation, Mapping):
            raise ValueError("review must contain a recommendation mapping")
        response = recommendation.get("response")
        if not isinstance(response, str):
            raise ValueError("recommendation response must be a string")
        if response != "increase_exploration_and_reassess":
            return {"status": "no_change", "reason": "recommendation_does_not_request_exploration",
                    "active_until_decision": self.active_until_decision, "epsilon": self.epsilon_for(decision_index)}
        evidence_ids = recommendation.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids or any(not isinstance(item, str) or not item for item in evidence_ids):
            raise ValueError("exploration activation requires non-empty evidence_ids")
        fingerprint = "|".join(sorted(set(evidence_ids)))
        if fingerprint in self._seen_evidence_fingerprints:
            return {"status": "duplicate_evidence", "reason": "review_evidence_already_consumed",
                    "active_until_decision": self.active_until_decision, "epsilon": self.epsilon_for(decision_index)}
        self._seen_evidence_fingerprints.add(fingerprint)
        self.active_until_decision = decision_index + self.duration_decisions - 1
        self.last_activation = {"decision_index": decision_index,
                                "active_until_decision": self.active_until_decision,
                                "evidence_ids": sorted(set(evidence_ids)),
                                "context": recommendation.get("context", "")}
        return {"status": "activated", "reason": "new_reward_drift_evidence",
                "active_until_decision": self.active_until_decision,
                "epsilon": self.epsilon_for(decision_index),
                "evidence_ids": self.last_activation["evidence_ids"]}

    def epsilon_for(self, decision_index: int) -> float:
        """Return the bounded epsilon for a decision index (inclusive expiry)."""
        decision_index = self._decision_index(decision_index)
        if self.active_until_decision is not None and decision_index <= self.active_until_decision:
            return self.elevated_epsilon
        return self.base_epsilon

    def snapshot(self) -> dict:
        """Return JSON-compatible controller state for checkpointing."""
        return {"schema_version": 1, "base_epsilon": self.base_epsilon,
                "elevated_epsilon": self.elevated_epsilon, "duration_decisions": self.duration_decisions,
                "active_until_decision": self.active_until_decision,
                "seen_evidence_fingerprints": sorted(self._seen_evidence_fingerprints),
                "last_activation": self.last_activation}

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNBoundedExplorationController":
        if not isinstance(data, Mapping) or data.get("schema_version") != 1:
            raise ValueError("unsupported exploration-controller snapshot schema")
        controller = cls(base_epsilon=data["base_epsilon"], elevated_epsilon=data["elevated_epsilon"],
                         duration_decisions=data["duration_decisions"])
        active_until = data.get("active_until_decision")
        if active_until is not None:
            controller._decision_index(active_until)
        fingerprints = data.get("seen_evidence_fingerprints")
        if not isinstance(fingerprints, list) or any(not isinstance(item, str) or not item for item in fingerprints):
            raise ValueError("snapshot evidence fingerprints must be non-empty strings")
        if len(set(fingerprints)) != len(fingerprints):
            raise ValueError("snapshot evidence fingerprints must be unique")
        last_activation = data.get("last_activation")
        if last_activation is not None and not isinstance(last_activation, Mapping):
            raise ValueError("snapshot last_activation must be a mapping or None")
        controller.last_activation = dict(last_activation) if last_activation is not None else None
        controller.active_until_decision = active_until
        controller._seen_evidence_fingerprints = set(fingerprints)
        return controller
