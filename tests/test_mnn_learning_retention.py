"""Tests for measurable learning improvement and checkpoint retention."""
from __future__ import annotations

import unittest

from benchmarks.mnn_learning_retention import run_benchmark


class MNNLearningRetentionBenchmarkTests(unittest.TestCase):
    def test_training_improves_toy_association_and_checkpoint_retains_it(self) -> None:
        result = run_benchmark()
        self.assertTrue(result["improvement"]["passed"], result)
        self.assertTrue(result["retention"]["passed"], result)
        self.assertEqual(
            result["after_training"]["cases"],
            result["after_checkpoint_restore"]["cases"],
        )

    def test_benchmark_rejects_invalid_training_rounds(self) -> None:
        with self.assertRaises(ValueError):
            run_benchmark(training_rounds=0)


if __name__ == "__main__":
    unittest.main()
