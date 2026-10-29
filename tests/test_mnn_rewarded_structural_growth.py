from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_rewarded_structural_growth import run_benchmark


class MNNRewardedStructuralGrowthTests(unittest.TestCase):
    def test_success_grows_and_failure_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark(
                checkpoint_path=Path(directory) / "rewarded-growth.json"
            )
        self.assertTrue(result["passed"], result)
        self.assertEqual(result["baseline_response_to_cue"], 0.0)
        self.assertEqual(result["failed_outcome_response_to_cue"], 0.0)
        self.assertEqual(result["trained_response_to_cue"], 0.75)
        self.assertEqual(result["restored_response_to_cue"], 0.75)
        self.assertEqual(len(result["grown_connections"]), 1)
        self.assertEqual(result["trained_weights"], result["restored_weights"])


if __name__ == "__main__":
    unittest.main()
