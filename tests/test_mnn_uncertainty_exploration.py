import json
import unittest

from machina.mnn_action_learning import MNNActionLearner
from benchmarks.mnn_uncertainty_exploration import run_benchmark, run_trial


class MNNUncertaintyExplorationTests(unittest.TestCase):
    def test_uncertainty_policy_is_reproducible_across_snapshot_restart(self):
        learner = MNNActionLearner(["left", "right"], exploration_seed=7)
        for _ in range(8):
            action = learner.choose(uncertainty_bonus=0.5)
            learner.observe(1.0 if action == "left" else 0.0)
        restored = MNNActionLearner.from_snapshot(json.loads(json.dumps(learner.snapshot())))
        self.assertEqual(
            learner.choose(uncertainty_bonus=0.5),
            restored.choose(uncertainty_bonus=0.5),
        )

    def test_uncertainty_parameter_validation_and_policy_exclusivity(self):
        learner = MNNActionLearner(["a", "b"])
        for value in (-1.0, float("nan"), float("inf"), True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    learner.choose(uncertainty_bonus=value)
        with self.assertRaises(ValueError):
            learner.choose(epsilon=0.1, uncertainty_bonus=0.2)

    def test_benchmark_is_reproducible_and_reports_both_policies(self):
        first = run_benchmark(seeds=(2, 5), rounds_per_phase=20)
        second = run_benchmark(seeds=(2, 5), rounds_per_phase=20)
        self.assertEqual(first, second)
        self.assertEqual(first["benchmark"], "mnn_uncertainty_exploration")
        self.assertTrue(any(row["policy"] == "epsilon_greedy" for row in first["summaries"]))
        self.assertTrue(any(row["policy"] == "uncertainty_bonus" for row in first["summaries"]))
        self.assertTrue(all("phase_2_mean_reward_rate" in row for row in first["summaries"]))

    def test_trial_rejects_unknown_policy(self):
        with self.assertRaises(ValueError):
            run_trial(policy="unknown", parameter=0.2, seed=1)


if __name__ == "__main__":
    unittest.main()
