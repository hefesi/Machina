import unittest

from benchmarks.mnn_exploration_sweep import run_sweep, run_trial


class MNNExplorationSweepTests(unittest.TestCase):
    def test_trial_is_reproducible_for_same_seed(self):
        first = run_trial(epsilon=0.15, seed=11, rounds_per_phase=20)
        second = run_trial(epsilon=0.15, seed=11, rounds_per_phase=20)
        self.assertEqual(first, second)

    def test_sweep_reports_reward_exploration_and_adaptation_metrics(self):
        result = run_sweep(epsilons=(0.0, 0.5), seeds=(1, 2), rounds_per_phase=20)
        self.assertEqual(result["benchmark"], "mnn_epsilon_greedy_exploration_sweep")
        self.assertEqual(len(result["summaries"]), 2)
        for summary in result["summaries"]:
            self.assertIn("phase_1_mean_reward_rate", summary)
            self.assertIn("phase_2_mean_reward_rate", summary)
            self.assertIn("mean_exploration_rate", summary)
            self.assertEqual(summary["adaptation_trials"], 2)
        self.assertEqual(len(result["trials"]), 4)

    def test_invalid_sweep_arguments_are_rejected(self):
        with self.assertRaises(ValueError):
            run_sweep(epsilons=())
        with self.assertRaises(ValueError):
            run_sweep(epsilons=(1.5,))
        with self.assertRaises(ValueError):
            run_sweep(seeds=())
        with self.assertRaises(ValueError):
            run_trial(epsilon=0.2, seed=1, rounds_per_phase=2)


if __name__ == "__main__":
    unittest.main()
