import json
import unittest

from machina.mnn_action_learning import MNNActionLearner


class MNNActionLearnerTests(unittest.TestCase):
    def test_explores_actions_and_learns_higher_reward_action(self):
        learner = MNNActionLearner(["left", "right"], learning_rate=0.5, exploration_interval=7)
        first = learner.choose()
        learner.observe(0.0)
        second = learner.choose()
        learner.observe(1.0)
        self.assertNotEqual(first, second)

        for _ in range(8):
            action = learner.choose()
            reward = 1.0 if action == "right" else 0.0
            learner.observe(reward)

        self.assertGreater(learner.predictions()["right"], learner.predictions()["left"])
        self.assertEqual(learner.counts["left"] + learner.counts["right"], 10)

    def test_adapts_after_reward_mapping_changes(self):
        learner = MNNActionLearner(["left", "right"], learning_rate=0.5, exploration_interval=3)
        for _ in range(40):
            action = learner.choose()
            learner.observe(1.0 if action == "left" else 0.0)
        self.assertGreater(learner.predictions()["left"], learner.predictions()["right"])

        for _ in range(80):
            action = learner.choose()
            learner.observe(1.0 if action == "right" else 0.0)
        self.assertGreater(learner.predictions()["right"], learner.predictions()["left"])

    def test_snapshot_retains_learned_values_and_exploration_state(self):
        learner = MNNActionLearner(["a", "b"], exploration_interval=4)
        for reward in (1.0, 0.0, 0.7):
            action = learner.choose()
            learner.observe(reward, action=action)
        restored = MNNActionLearner.from_snapshot(json.loads(json.dumps(learner.snapshot())))
        self.assertEqual(restored.snapshot(), learner.snapshot())
        self.assertEqual(restored.choose(), learner.choose())

    def test_epsilon_greedy_is_reproducible_and_explores(self):
        first = MNNActionLearner(["left", "right"], exploration_seed=17)
        second = MNNActionLearner(["left", "right"], exploration_seed=17)
        # Initial unseen-action coverage is guaranteed, then epsilon=1 explores.
        for learner in (first, second):
            action = learner.choose(epsilon=1.0)
            learner.observe(0.0, action=action)
            action = learner.choose(epsilon=1.0)
            learner.observe(0.0, action=action)
        sequence_a = [first.choose(epsilon=1.0) for _ in range(20)]
        sequence_b = [second.choose(epsilon=1.0) for _ in range(20)]
        self.assertEqual(sequence_a, sequence_b)

    def test_epsilon_greedy_rejects_invalid_epsilon(self):
        learner = MNNActionLearner(["a", "b"])
        for epsilon in (-0.1, 1.1, float("nan"), True):
            with self.subTest(epsilon=epsilon):
                with self.assertRaises(ValueError):
                    learner.choose(epsilon=epsilon)

    def test_snapshot_preserves_exploration_seed_and_legacy_default(self):
        learner = MNNActionLearner(["a", "b"], exploration_seed=42)
        snapshot = json.loads(json.dumps(learner.snapshot()))
        restored = MNNActionLearner.from_snapshot(snapshot)
        self.assertEqual(restored.exploration_seed, 42)
        snapshot.pop("exploration_seed")
        legacy = MNNActionLearner.from_snapshot(snapshot)
        self.assertEqual(legacy.exploration_seed, 0)

    def test_invalid_rewards_and_snapshot_counts_are_rejected(self):
        learner = MNNActionLearner(["a", "b"])
        with self.assertRaises(ValueError):
            learner.observe(float("nan"), action="a")
        data = learner.snapshot()
        data["counts"]["a"] = -1
        with self.assertRaises(ValueError):
            MNNActionLearner.from_snapshot(data)

    def test_unknown_action_is_rejected(self):
        learner = MNNActionLearner(["a", "b"])
        with self.assertRaises(ValueError):
            learner.observe(1.0, action="missing")


if __name__ == "__main__":
    unittest.main()
