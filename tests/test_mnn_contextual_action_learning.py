import json
import unittest

from machina.mnn_contextual_action_learning import MNNContextualActionLearner


class MNNContextualActionLearnerTests(unittest.TestCase):
    def train_context(self, learner, context, preferred):
        for _ in range(3):
            for action in ("left", "right"):
                learner.observe(context, action, 1.0 if action == preferred else 0.0)

    def test_learns_opposite_action_preferences_for_distinct_contexts(self):
        learner = MNNContextualActionLearner(["left", "right"], min_samples_per_action=2)
        self.train_context(learner, "quiet workload", "left")
        self.train_context(learner, "busy workload", "right")

        quiet = learner.recommend("workload quiet")
        busy = learner.recommend("BUSY, workload!")

        self.assertEqual(quiet["status"], "recommended")
        self.assertEqual(quiet["action"], "left")
        self.assertEqual(busy["status"], "recommended")
        self.assertEqual(busy["action"], "right")

    def test_unseen_context_abstains_instead_of_using_global_preference(self):
        learner = MNNContextualActionLearner(["left", "right"])
        self.train_context(learner, "quiet workload", "left")
        result = learner.recommend("stormy evening")
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "insufficient_contextual_observations")

    def test_abstains_when_contextual_values_are_too_close(self):
        learner = MNNContextualActionLearner(
            ["left", "right"], min_samples_per_action=2, min_reward_margin=0.1
        )
        for action in ("left", "right"):
            for reward in (0.5, 0.55):
                learner.observe("quiet room", action, reward)
        result = learner.recommend("room quiet")
        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "contextual_values_too_close")

    def test_snapshot_round_trip_preserves_context_values(self):
        learner = MNNContextualActionLearner(["left", "right"])
        self.train_context(learner, "quiet workload", "left")
        snapshot = json.loads(json.dumps(learner.snapshot(), allow_nan=False))
        restored = MNNContextualActionLearner.from_snapshot(snapshot)
        self.assertEqual(restored.snapshot(), snapshot)
        self.assertEqual(restored.recommend("workload quiet")["action"], "left")

    def test_reward_updates_only_the_matching_context_table(self):
        learner = MNNContextualActionLearner(["left", "right"], learning_rate=0.5)
        learner.observe("quiet room", "left", 1.0)
        learner.observe("busy room", "left", -1.0)
        self.assertEqual(learner.recommend("quiet room")["status"], "abstain")
        self.assertEqual(learner.snapshot()["values"]["busy room"]["left"], -1.0)

    def test_generalizes_to_related_context_with_weighted_lexical_evidence(self):
        learner = MNNContextualActionLearner(
            ["left", "right"], min_samples_per_action=2, min_context_similarity=0.6
        )
        self.train_context(learner, "quiet workload", "left")
        self.train_context(learner, "busy workload", "right")

        result = learner.recommend("quiet workload today")

        self.assertEqual(result["status"], "recommended")
        self.assertEqual(result["action"], "left")
        self.assertEqual(result["contributing_contexts"], [
            {"context": "quiet workload", "similarity": 2 / 3}
        ])
        self.assertGreaterEqual(result["effective_sample_counts"]["left"], 2)

    def test_unrelated_contexts_do_not_transfer_evidence(self):
        learner = MNNContextualActionLearner(
            ["left", "right"], min_samples_per_action=1, min_context_similarity=0.5
        )
        self.train_context(learner, "quiet workload", "left")
        result = learner.recommend("stormy evening")

        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "insufficient_similar_context_evidence")
        self.assertEqual(result["contributing_contexts"], [])

    def test_conflicting_similar_contexts_can_force_abstention(self):
        learner = MNNContextualActionLearner(
            ["left", "right"], min_samples_per_action=1,
            min_reward_margin=0.2, min_context_similarity=0.5
        )
        self.train_context(learner, "quiet workload", "left")
        self.train_context(learner, "quiet workload today", "right")

        result = learner.recommend("quiet workload now")

        self.assertEqual(result["status"], "abstain")
        self.assertEqual(result["reason"], "contextual_values_too_close")

    def test_schema_one_snapshot_restores_exact_match_only_compatibility(self):
        learner = MNNContextualActionLearner(["left", "right"])
        self.train_context(learner, "quiet workload", "left")
        legacy = learner.snapshot()
        legacy["schema_version"] = 1
        legacy.pop("min_context_similarity")
        restored = MNNContextualActionLearner.from_snapshot(legacy)

        self.assertEqual(restored.min_context_similarity, 1.0)
        self.assertEqual(restored.recommend("quiet workload today")["status"], "abstain")
        self.assertEqual(restored.recommend("workload quiet")["action"], "left")

    def test_validates_inputs(self):
        with self.assertRaises(ValueError):
            MNNContextualActionLearner(["left", "left"])
        learner = MNNContextualActionLearner(["left", "right"])
        with self.assertRaises(ValueError):
            learner.observe("quiet", "unknown", 1.0)
        with self.assertRaises(ValueError):
            learner.observe("quiet", "left", float("nan"))
        with self.assertRaises(ValueError):
            learner.recommend("!!!")


if __name__ == "__main__":
    unittest.main()
