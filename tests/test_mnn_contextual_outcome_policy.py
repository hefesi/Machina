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


    def test_partial_shared_word_is_not_enough_context_overlap(self):
        self.add_outcome("left-1", "left", 1.0, "stable workload")
        self.add_outcome("left-2", "left", 1.0, "stable workload")
        self.add_outcome("right-1", "right", 0.0, "risky workload")
        self.add_outcome("right-2", "right", 0.0, "risky workload")

        result = MNNContextualOutcomePolicy(
            self.memory, ["left", "right"], min_samples_per_action=2,
        ).recommend("stable workload")

        self.assertEqual("abstain", result["status"])
        self.assertEqual(0, result["sample_counts"]["right"])

    def test_reads_persistent_archive_without_mutating_memory(self):
        self.add_outcome("left-1", "left", 1.0)
        self.add_outcome("left-2", "left", 1.0)
        self.add_outcome("right-1", "right", 0.0)
        self.add_outcome("right-2", "right", 0.0)
        before_count = self.memory.count()

        result = MNNContextualOutcomePolicy(self.memory, ["left", "right"]).recommend("quiet morning")

        self.assertEqual(result["status"], "recommended")
        self.assertEqual(self.memory.count(), before_count)

    def test_recency_weighting_adapts_after_reward_reversal(self):
        # Older evidence favours left; newer evidence favours right.
        for index in range(1, 4):
            self.memory.add(
                "old left outcome", kind="action-outcome",
                source_uri=f"test://old-left-{index}", confidence=1.0,
                metadata={"action": "left", "reward": 1.0,
                          "context": "quiet morning", "decision": index},
                fragment_id=f"old-left-{index}",
            )
            self.memory.add(
                "old right outcome", kind="action-outcome",
                source_uri=f"test://old-right-{index}", confidence=1.0,
                metadata={"action": "right", "reward": 0.0,
                          "context": "quiet morning", "decision": index},
                fragment_id=f"old-right-{index}",
            )
        for index in range(4, 7):
            self.memory.add(
                "new left outcome", kind="action-outcome",
                source_uri=f"test://new-left-{index}", confidence=1.0,
                metadata={"action": "left", "reward": 0.0,
                          "context": "quiet morning", "decision": index},
                fragment_id=f"new-left-{index}",
            )
            self.memory.add(
                "new right outcome", kind="action-outcome",
                source_uri=f"test://new-right-{index}", confidence=1.0,
                metadata={"action": "right", "reward": 1.0,
                          "context": "quiet morning", "decision": index},
                fragment_id=f"new-right-{index}",
            )

        before_count = self.memory.count()
        all_history = MNNContextualOutcomePolicy(
            self.memory, ["left", "right"], min_samples_per_action=2,
            min_reward_margin=0.1,
        ).recommend("quiet morning")
        recency = MNNContextualOutcomePolicy(
            self.memory, ["left", "right"], min_samples_per_action=2,
            min_reward_margin=0.1, recency_half_life_decisions=1.0,
        ).recommend("quiet morning")

        self.assertEqual(all_history["status"], "recommended")
        self.assertEqual(all_history["action"], "left")
        self.assertEqual(recency["status"], "recommended")
        self.assertEqual(recency["action"], "right")
        self.assertEqual(self.memory.count(), before_count)
        self.assertEqual(recency["sample_counts"], {"left": 6, "right": 6})

    def test_recency_weighting_preserves_legacy_fragments_without_decision(self):
        self.add_outcome("left-1", "left", 1.0)
        self.add_outcome("left-2", "left", 1.0)
        self.add_outcome("right-1", "right", 0.0)
        self.add_outcome("right-2", "right", 0.0)
        result = MNNContextualOutcomePolicy(
            self.memory, ["left", "right"], recency_half_life_decisions=2.0
        ).recommend("quiet morning")
        self.assertEqual(result["status"], "recommended")
        self.assertEqual(result["action"], "left")

    def test_validates_recency_half_life(self):
        for value in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    MNNContextualOutcomePolicy(
                        self.memory, ["left", "right"],
                        recency_half_life_decisions=value,
                    )

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
