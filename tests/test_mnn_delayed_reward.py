import unittest

from benchmarks.mnn_delayed_reward import run_benchmark


class MNNDelayedRewardBenchmarkTests(unittest.TestCase):
    def test_delayed_reward_uses_prior_eligibility(self):
        result = run_benchmark()
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["initial_weight"], result["immediate_hebbian_weight"])
        self.assertGreater(result["eligibility_weight"], result["initial_weight"])
        self.assertGreater(result["eligibility_trace_at_reward"], 0.0)

    def test_longer_delay_reduces_trace_contribution(self):
        short = run_benchmark(delay_steps=1)
        long = run_benchmark(delay_steps=5)
        self.assertTrue(short["passed"], short)
        self.assertTrue(long["passed"], long)
        self.assertLess(long["eligibility_weight_delta"], short["eligibility_weight_delta"])

    def test_benchmark_is_deterministic(self):
        self.assertEqual(run_benchmark(), run_benchmark())

    def test_invalid_parameters_are_rejected(self):
        for rate in (-0.1, float("nan"), float("inf"), True):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    run_benchmark(learning_rate=rate)
        for delay in (0, -1, True, 1.5):
            with self.subTest(delay=delay):
                with self.assertRaises(ValueError):
                    run_benchmark(delay_steps=delay)


if __name__ == "__main__":
    unittest.main()
