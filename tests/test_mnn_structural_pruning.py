from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_structural_pruning import run_benchmark


class MNNStructuralPruningBenchmarkTests(unittest.TestCase):
    def test_grown_edge_is_pruned_only_after_repeated_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark(
                checkpoint_path=Path(directory) / "structural-pruning.json"
            )
        self.assertTrue(result["passed"], result)
        self.assertEqual(
            result["pruning"]["after_growth_response_to_cue"], 0.75
        )
        self.assertEqual(
            result["pruning"]["first_failure_response_to_cue"], 0.75
        )
        self.assertEqual(
            result["pruning"]["utility_after_restart"],
            {"grown:cue->response": -1},
        )
        self.assertEqual(
            result["pruning"]["after_pruning_response_to_cue"], 0.0
        )
        self.assertFalse(result["pruning"]["edge_exists_after_reload"])
        self.assertEqual(result["control"]["control_response_to_cue"], 0.75)
        self.assertTrue(result["control"]["control_edge_exists"])


if __name__ == "__main__":
    unittest.main()
