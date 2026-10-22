import unittest

from benchmarks.mnn_reward_learning import run_benchmark


class MNNBenchmarkTests(unittest.TestCase):
    def test_reward_plasticity_learns_toy_two_context_association(self):
        result = run_benchmark(training_rounds=8, learning_rate=0.5)
        baseline = result["baseline_fixed_weights"]
        trained = result["trained_reward_plasticity"]

        self.assertEqual(baseline["accuracy"], 0.5)
        self.assertEqual(trained["accuracy"], 1.0)
        self.assertLess(trained["mean_squared_error"], baseline["mean_squared_error"])
        self.assertGreater(result["final_weights"]["positive_to_response"], 0.0)
        self.assertLess(result["final_weights"]["negative_to_response"], 0.0)

    def test_benchmark_is_deterministic(self):
        self.assertEqual(
            run_benchmark(training_rounds=4, learning_rate=0.25),
            run_benchmark(training_rounds=4, learning_rate=0.25),
        )

    def test_rejects_invalid_training_rounds(self):
        with self.assertRaises(ValueError):
            run_benchmark(training_rounds=0)
        with self.assertRaises(ValueError):
            run_benchmark(training_rounds=True)


if __name__ == "__main__":
    unittest.main()
