from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_experience_learning import run_benchmark


class MNNExperienceLearningTests(unittest.TestCase):
    def test_delayed_experience_learns_and_survives_checkpoint(self):
        result = run_benchmark()
        self.assertTrue(result["passed"], result)
        self.assertEqual(0.5, result["baseline_fixed_weights"]["accuracy"])
        self.assertEqual(1.0, result["trained_with_delayed_experience"]["accuracy"])
        self.assertEqual(1.0, result["restored_after_checkpoint"]["accuracy"])
        self.assertTrue(result["weights_preserved"])
        self.assertEqual(0, result["pending_steps_after_restore"])
        self.assertGreater(result["trained_weights"]["positive_to_response"], 0.0)
        self.assertLess(result["trained_weights"]["negative_to_response"], 0.0)

    def test_explicit_checkpoint_path_preserves_behavior(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "experience.json"
            result = run_benchmark(checkpoint_path=path)
            self.assertTrue(result["passed"], result)
            self.assertTrue(path.exists())

    def test_benchmark_is_deterministic(self):
        self.assertEqual(run_benchmark(), run_benchmark())

    def test_invalid_parameters_are_rejected(self):
        for rounds in (0, -1, True, 1.5):
            with self.subTest(rounds=rounds):
                with self.assertRaises(ValueError):
                    run_benchmark(training_rounds=rounds)
        for rate in (-0.1, float("nan"), float("inf"), True):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    run_benchmark(learning_rate=rate)


if __name__ == "__main__":
    unittest.main()
