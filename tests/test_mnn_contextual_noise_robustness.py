import unittest

from benchmarks.mnn_contextual_noise_robustness import run_benchmark


class MNNContextualNoiseRobustnessTests(unittest.TestCase):
    def test_generalization_improves_coverage_under_noisy_rewards(self):
        result = run_benchmark(seeds=20, observations_per_action=24)
        exact = result["exact_match"]
        generalized = result["generalized"]

        self.assertTrue(result["synthetic_only"])
        self.assertEqual(exact["coverage"], 0.0)
        self.assertEqual(exact["abstentions"], 40)
        self.assertEqual(generalized["coverage"], 1.0)
        self.assertGreaterEqual(generalized["accuracy_when_recommended"], 0.75)
        self.assertEqual(generalized["recommendations"], 40)
        self.assertEqual(len(result["records"]), 20)

    def test_rejects_invalid_benchmark_dimensions(self):
        with self.assertRaises(ValueError):
            run_benchmark(seeds=0)
        with self.assertRaises(ValueError):
            run_benchmark(observations_per_action=0)


if __name__ == "__main__":
    unittest.main()
