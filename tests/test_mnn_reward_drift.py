import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_reward_drift import MNNRewardDriftDetector


class MNNRewardDriftDetectorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.tempdir.name) / "memory.sqlite3")

    def tearDown(self):
        self.memory.close()
        self.tempdir.cleanup()

    def add(self, decision, action, reward, context="stable workload"):
        return self.memory.add(
            f"Decision {decision}: {action} got {reward}",
            kind="action-outcome",
            source_uri=f"test://decision-{decision}-{action}",
            confidence=1.0,
            metadata={"decision": decision, "action": action,
                      "reward": reward, "context": context},
            fragment_id=f"decision-{decision}-{action}",
        )

    def test_detects_persistent_reward_reversal_without_deleting_history(self):
        for decision in range(1, 5):
            self.add(decision, "continue", 1.0)
            self.add(decision, "pause", 0.0)
        for decision in range(5, 9):
            self.add(decision, "continue", 0.0)
            self.add(decision, "pause", 1.0)
        before = self.memory.count()

        result = MNNRewardDriftDetector(
            self.memory, decisions_per_window=4,
            min_samples_per_action_window=3, min_reward_shift=0.5,
        ).detect("stable workload")

        self.assertEqual(result["status"], "detected")
        self.assertEqual(set(result["shifted_actions"]), {"continue", "pause"})
        self.assertEqual(result["comparisons"]["continue"]["reward_shift"], -1.0)
        self.assertEqual(result["comparisons"]["pause"]["reward_shift"], 1.0)
        self.assertEqual(self.memory.count(), before)

    def test_abstains_without_two_windows(self):
        for decision in range(1, 4):
            self.add(decision, "continue", 1.0)
        result = MNNRewardDriftDetector(
            self.memory, decisions_per_window=2
        ).detect("stable workload")
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "insufficient_decision_history")

    def test_ignores_unrelated_context(self):
        for decision in range(1, 9):
            self.add(decision, "continue", 1.0 if decision < 5 else 0.0,
                     context="stable workload" if decision < 5 else "risky workload")
        result = MNNRewardDriftDetector(
            self.memory, decisions_per_window=4
        ).detect("stable workload")
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "insufficient_decision_history")

    def test_reports_stable_when_rewards_do_not_shift(self):
        for decision in range(1, 9):
            self.add(decision, "continue", 0.5)
            self.add(decision, "pause", 0.4)
        result = MNNRewardDriftDetector(
            self.memory, decisions_per_window=4, min_reward_shift=0.3
        ).detect("stable workload")
        self.assertEqual(result["status"], "stable")
        self.assertEqual(result["shifted_actions"], [])

    def test_validates_configuration(self):
        for kwargs in (
            {"decisions_per_window": 1},
            {"min_samples_per_action_window": 0},
            {"min_reward_shift": 0},
            {"min_context_overlap": 0},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    MNNRewardDriftDetector(self.memory, **kwargs)


if __name__ == "__main__":
    unittest.main()
