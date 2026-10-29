from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_structural_growth import run_benchmark


class MNNStructuralGrowthBenchmarkTests(unittest.TestCase):
    def test_growth_adds_a_path_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark(
                checkpoint_path=Path(directory) / "structural-growth.json"
            )
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["baseline_response_to_cue"], 0.0)
        self.assertEqual(result["trained_response_to_cue"], 0.75)
        self.assertEqual(result["restored_response_to_cue"], 0.75)
        self.assertEqual(len(result["grown_connections"]), 1)
        self.assertEqual(result["trained_weights"], result["restored_weights"])

    def test_invalid_initial_weight_is_rejected(self):
        for weight in (0, -0.1, float("nan"), float("inf"), True):
            with self.subTest(weight=weight):
                with self.assertRaises(ValueError):
                    run_benchmark(initial_weight=weight)


if __name__ == "__main__":
    unittest.main()
