"""Integration tests for reward-drift review in the MNN agent."""
import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent
from machina.mnn_reward_drift import MNNRewardDriftDetector


class MNNAgentDriftReviewTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.tempdir.name) / "memory.sqlite3")
        for decision in range(1, 5):
            self.add(decision, "continue", 1.0)
            self.add(decision, "pause", 0.0)
        for decision in range(5, 9):
            self.add(decision, "continue", 0.0)
            self.add(decision, "pause", 1.0)

    def tearDown(self):
        self.memory.close()
        self.tempdir.cleanup()

    def add(self, decision, action, reward):
        self.memory.add(
            f"Decision {decision}: {action} reward {reward}",
            kind="action-outcome",
            source_uri=f"test://{decision}-{action}",
            confidence=1.0,
            metadata={"decision": decision, "action": action, "reward": reward,
                      "context": "stable workload"},
            fragment_id=f"evidence-{decision}-{action}",
        )

    def test_agent_surfaces_drift_and_requests_review_without_switching_policy(self):
        learner = MNNActionLearner(["continue", "pause"])
        detector = MNNRewardDriftDetector(
            self.memory, decisions_per_window=4,
            min_samples_per_action_window=3, min_reward_shift=0.5,
        )
        agent = MNNLearningAgent(learner, self.memory, reward_drift_detector=detector)
        before = self.memory.count()

        decision = agent.decide(context="stable workload", review_reward_drift=True)

        self.assertEqual("detected", decision["reward_drift_review"]["status"])
        self.assertTrue(decision["request_experience"])
        self.assertEqual("learner", decision["selection_source"])
        self.assertEqual(1, learner.decisions)
        self.assertEqual(before, self.memory.count())
        agent.resolve(0.25, context="stable workload")

    def test_review_is_opt_in_and_requires_detector_and_context(self):
        learner = MNNActionLearner(["continue", "pause"])
        agent = MNNLearningAgent(learner, self.memory)
        with self.assertRaises(ValueError):
            agent.decide(context="stable workload", review_reward_drift=True)
        self.assertEqual(0, learner.decisions)

        detector = MNNRewardDriftDetector(self.memory, decisions_per_window=4)
        configured = MNNLearningAgent(learner, self.memory, reward_drift_detector=detector)
        with self.assertRaises(ValueError):
            configured.decide(review_reward_drift=True)
        self.assertEqual(0, learner.decisions)

    def test_detector_must_share_agent_memory(self):
        other = FragmentMemory(Path(self.tempdir.name) / "other.sqlite3")
        try:
            detector = MNNRewardDriftDetector(other)
            with self.assertRaises(ValueError):
                MNNLearningAgent(MNNActionLearner(["continue", "pause"]),
                                 self.memory, reward_drift_detector=detector)
        finally:
            other.close()


if __name__ == "__main__":
    unittest.main()
