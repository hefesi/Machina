"""Regression tests for stochastic MNN adaptation across multiple seeds."""
from __future__ import annotations

import unittest

from benchmarks.mnn_stochastic_adaptation import run_benchmark


class MNNStochasticAdaptationTests(unittest.TestCase):
    def test_adapts_after_noisy_reward_reversal_and_beats_random_baseline(self):
        result = run_benchmark(seeds=12, trials_per_phase=100)

        self.assertTrue(result["passed"], result["aggregate"])
        self.assertGreaterEqual(result["aggregate"]["phase_1_reward_rate"], 0.68)
        self.assertGreaterEqual(result["aggregate"]["phase_2_last_60_reward_rate"], 0.65)
        self.assertGreaterEqual(
            result["aggregate"]["adaptation_minus_random_baseline"], 0.10
        )
        self.assertEqual(len(result["per_seed"]), 12)

    def test_rejects_too_few_seeds_and_trials(self):
        with self.assertRaises(ValueError):
            run_benchmark(seeds=4)
        with self.assertRaises(ValueError):
            run_benchmark(trials_per_phase=59)


if __name__ == "__main__":
    unittest.main()
