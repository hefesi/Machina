import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_reward_drift import MNNRewardDriftDetector
from machina.mnn_strategy_review import MNNStrategyReviewer


class StrategyReviewerTests(unittest.TestCase):
    def test_candidate_requires_drift_and_compares_recent_rewards(self):
        with tempfile.TemporaryDirectory() as tmp:
            with FragmentMemory(Path(tmp) / "memory.db") as memory:
                for decision in range(1, 5):
                    for action, reward in (("keep", 1.0), ("switch", 0.0)):
                        memory.add("workload context", kind="action-outcome",
                            source_uri=f"test://{decision}-{action}", confidence=1.0,
                            metadata={"decision": decision, "action": action, "reward": reward,
                                      "context": "workload context"})
                for decision in range(5, 9):
                    for action, reward in (("keep", 0.0), ("switch", 1.0)):
                        memory.add("workload context", kind="action-outcome",
                            source_uri=f"test://{decision}-{action}", confidence=1.0,
                            metadata={"decision": decision, "action": action, "reward": reward,
                                      "context": "workload context"})
                detector = MNNRewardDriftDetector(memory, decisions_per_window=4,
                    min_samples_per_action_window=3, min_reward_shift=0.5)
                reviewer = MNNStrategyReviewer(detector, ["keep", "switch"],
                    min_recent_samples=3, min_reward_margin=0.5)
                result = reviewer.review("workload context", current_action="keep")
                self.assertEqual("candidate", result["status"])
                self.assertEqual("switch", result["candidate_action"])
                self.assertTrue(result["evidence"]["switch"]["recent_evidence_ids"])


if __name__ == "__main__":
    unittest.main()
