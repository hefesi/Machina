import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_contextual_outcome_policy import MNNContextualOutcomePolicy


class MNNContextualOutcomePolicyTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.tempdir.name) / "memory.sqlite3")

    def tearDown(self):
        self.memory.close()
        self.tempdir.cleanup()

    def add_outcome(self, identifier, action, reward, context="quiet morning"):
        return self.memory.add(
            f"Observed {action} in {context} with reward {reward}",
            kind="action-outcome",
            source_uri=f"test://{identifier}",
            confidence=1.0,
            tags=("action-learning", action),
            metadata={"action": action, "reward": reward, "context": context},
            fragment_id=identifier,
        )

    def test_recommends_action_from_repeated_contextual_rewards(self):
        for index, reward in enumerate((1.0, 0.8, 1.0)):
            self.add_outcome(f"left-{index}", "left", reward)
        for index, reward in enumerate((0.0, 0.1, 0.0)):
            self.add_outcome(f"right-{index}", "right", reward)

        policy = MNNContextualOutcomePolicy(self.memory, ["left", "right"], min_samples_per_action=2)
        result = policy.recommend("quiet morning")

        self.assertEqual(result["status"], "recommended")
        self.assertEqual(result["action"], "left")
        self.assertEqual(result["sample_counts"], {"left": 3, "right": 3})
        self.assertEqual(len(result["evidence_ids"]["left"]), 3)
        self.assertGreaterEqual(result["reward_margin"], 0.1)

    def test_abstains_when_any_action_lacks_minimum_evidence(self):
        self.add_outcome("left-1", "left", 1.0)
        self.add_outcome("left-2", "left", 0.8)
        self.add_outcome("right-1", "right", 0.0)

        result = MNNContextualOutcomePolicy(
            self.memory, ["left", "right"], min_samples_per_action=2
        ).recommend("quiet morning")

        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "insufficient_comparable_evidence")
        self.assertEqual(result["missing_actions"], ["right"])

    def test_abstains_when_estimated_rewards_are_too_close(self):
        for action, rewards in (("left", (0.5, 0.6)), ("right", (0.55, 0.55))):
            for index, reward in enumerate(rewards):
                self.add_outcome(f"{action}-{index}", action, reward)

        result = MNNContextualOutcomePolicy(
            self.memory, ["left", "right"], min_samples_per_action=2,
            min_reward_margin=0.1,
        ).recommend("quiet morning")

        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "reward_estimates_too_close")

    def test_context_overlap_filters_unrelated_outcomes(self):
        self.add_outcome("left-1", "left", 1.0, "quiet morning")
        self.add_outcome("left-2", "left", 1.0, "quiet morning")
        self.add_outcome("right-1", "right", 0.0, "noisy evening")
        self.add_outcome("right-2", "right", 0.0, "noisy evening")

        result = MNNContextualOutcomePolicy(
            self.memory, ["left", "right"], min_samples_per_action=2,
        ).recommend("quiet morning")

        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["sample_counts"]["right"], 0)

    def test_reads_persistent_archive_without_mutating_memory(self):
        self.add_outcome("left-1", "left", 1.0)
        self.add_outcome("left-2", "left", 1.0)
        self.add_outcome("right-1", "right", 0.0)
        self.add_outcome("right-2", "right", 0.0)
        before_count = self.memory.count()

        result = MNNContextualOutcomePolicy(self.memory, ["left", "right"]).recommend("quiet morning")

        self.assertEqual(result["status"], "recommended")
        self.assertEqual(self.memory.count(), before_count)

    def test_validates_configuration_and_query(self):
        with self.assertRaises(ValueError):
            MNNContextualOutcomePolicy(self.memory, ["left", "left"])
        with self.assertRaises(ValueError):
            MNNContextualOutcomePolicy(self.memory, ["left", "right"], min_samples_per_action=0)
        policy = MNNContextualOutcomePolicy(self.memory, ["left", "right"])
        with self.assertRaises(ValueError):
            policy.recommend("  ")


if __name__ == "__main__":
    unittest.main()
