import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_adaptive_review import MNNAdaptiveReviewCycle
from machina.mnn_reward_drift import MNNRewardDriftDetector


class MNNAdaptiveReviewCycleTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.tempdir.name) / "memory.sqlite3")

    def tearDown(self):
        self.memory.close()
        self.tempdir.cleanup()

    def add(self, decision, action, reward, context="stable workload"):
        self.memory.add(
            f"Decision {decision}: {action} got {reward}",
            kind="action-outcome",
            source_uri=f"test://decision-{decision}-{action}",
            confidence=1.0,
            metadata={"decision": decision, "action": action,
                      "reward": reward, "context": context},
            fragment_id=f"decision-{decision}-{action}",
        )

    def test_review_connects_detector_to_response_without_side_effects(self):
        for decision in range(1, 5):
            self.add(decision, "continue", 1.0)
            self.add(decision, "pause", 0.0)
        for decision in range(5, 9):
            self.add(decision, "continue", 0.0)
            self.add(decision, "pause", 1.0)
        before = self.memory.count()
        cycle = MNNAdaptiveReviewCycle(
            self.memory,
            detector=MNNRewardDriftDetector(
                self.memory, decisions_per_window=4,
                min_samples_per_action_window=3, min_reward_shift=0.5,
            ),
        )

        result = cycle.review("stable workload")

        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["detection"]["status"], "detected")
        self.assertEqual(result["recommendation"]["response"], "increase_exploration_and_reassess")
        self.assertEqual(result["recommendation"]["degraded_actions"], ["continue"])
        self.assertEqual(result["recommendation"]["improved_actions"], ["pause"])
        self.assertEqual(result["memory_count"], before)
        self.assertEqual(self.memory.count(), before)
        self.assertEqual(result["side_effects"], {
            "memory_written": False,
            "learner_modified": False,
            "history_deleted": False,
        })

    def test_review_propagates_abstention_as_request_for_more_evidence(self):
        cycle = MNNAdaptiveReviewCycle(self.memory)
        result = cycle.review("new context")
        self.assertEqual(result["detection"]["status"], "abstain")
        self.assertEqual(result["recommendation"]["response"], "collect_more_evidence")

    def test_rejects_detector_bound_to_different_memory(self):
        other_path = Path(self.tempdir.name) / "other.sqlite3"
        with FragmentMemory(other_path) as other_memory:
            detector = MNNRewardDriftDetector(other_memory)
            with self.assertRaises(ValueError):
                MNNAdaptiveReviewCycle(self.memory, detector=detector)

    def test_rejects_invalid_context(self):
        cycle = MNNAdaptiveReviewCycle(self.memory)
        with self.assertRaises(ValueError):
            cycle.review("")


if __name__ == "__main__":
    unittest.main()
