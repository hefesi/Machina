import unittest

from benchmarks.mnn_context_transfer import run_benchmark


class MNNContextTransferBenchmarkTests(unittest.TestCase):
    def test_generalized_policy_increases_coverage_without_losing_synthetic_accuracy(self):
        result = run_benchmark()
        exact = result["exact_match"]
        generalized = result["generalized"]

        self.assertTrue(result["synthetic_only"])
        self.assertEqual(exact["recommendations"], 0)
        self.assertEqual(exact["abstentions"], exact["cases"])
        self.assertEqual(generalized["recommendations"], generalized["cases"])
        self.assertEqual(generalized["correct_recommendations"], generalized["cases"])
        self.assertEqual(generalized["accuracy_when_recommended"], 1.0)
        self.assertGreater(generalized["coverage"], exact["coverage"])


if __name__ == "__main__":
    unittest.main()
