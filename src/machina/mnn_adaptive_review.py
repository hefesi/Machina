"""Compose reward-drift detection and conservative response into one review cycle."""
from __future__ import annotations

from .fragment_memory import FragmentMemory
from .mnn_drift_response import MNNDriftResponsePolicy
from .mnn_reward_drift import MNNRewardDriftDetector


class MNNAdaptiveReviewCycle:
    """Run a repeatable, read-only review of reward drift for one context.

    This is a monitoring/controller boundary, not an autonomous action selector.
    It never writes to memory or changes the learner; callers decide whether and
    how to apply the recommendation.
    """

    def __init__(
        self,
        memory: FragmentMemory,
        *,
        detector: MNNRewardDriftDetector | None = None,
        response_policy: MNNDriftResponsePolicy | None = None,
    ) -> None:
        if not isinstance(memory, FragmentMemory):
            raise ValueError("memory must be a FragmentMemory")
        if detector is not None and not isinstance(detector, MNNRewardDriftDetector):
            raise ValueError("detector must be an MNNRewardDriftDetector")
        if response_policy is not None and not isinstance(response_policy, MNNDriftResponsePolicy):
            raise ValueError("response_policy must be an MNNDriftResponsePolicy")
        if detector is not None and detector.memory is not memory:
            raise ValueError("detector must use the same memory instance")
        self.memory = memory
        self.detector = detector or MNNRewardDriftDetector(memory)
        self.response_policy = response_policy or MNNDriftResponsePolicy()

    def review(self, context: str) -> dict:
        """Return raw evidence and the corresponding conservative recommendation."""
        detection = self.detector.detect(context)
        recommendation = self.response_policy.evaluate(detection)
        return {
            "schema_version": 1,
            "context": context.strip(),
            "detection": detection,
            "recommendation": recommendation,
            "memory_count": self.memory.count(),
            "side_effects": {
                "memory_written": False,
                "learner_modified": False,
                "history_deleted": False,
            },
        }
