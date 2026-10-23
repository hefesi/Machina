from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_retention_interference import run_benchmark


class MNNRetentionInterferenceTests(unittest.TestCase):
    def test_retention_interference_and_checkpoint_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark(
                checkpoint_path=Path(directory) / "retention.json"
            )

        self.assertTrue(result["passed"], result)
        initial = result["initial_learning"]
        unrelated = result["after_unrelated_learning"]
        omitted = result["cue_omission_probe"]
        interfered = result["after_conflicting_learning"]
        restored = result["after_checkpoint_restore"]

        self.assertTrue(initial["retained"])
        self.assertTrue(unrelated["retained"])
        self.assertTrue(unrelated["weight_unchanged"])
        self.assertEqual(0.0, omitted["output_without_either_cue"])
        self.assertTrue(omitted["original_association_weight_still_present"])
        self.assertFalse(interfered["original_association_retained"])
        self.assertTrue(interfered["behavior_changed"])
        self.assertTrue(restored["weights_preserved"])
        self.assertTrue(restored["behavior_preserved"])

    def test_invalid_learning_rate_and_round_counts_are_rejected(self):
        for rate in (0, -0.1, float("nan"), float("inf")):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    run_benchmark(learning_rate=rate)

        for parameter in ("initial_rounds", "unrelated_rounds", "interference_rounds"):
            with self.subTest(parameter=parameter):
                with self.assertRaises(ValueError):
                    run_benchmark(**{parameter: 0})


if __name__ == "__main__":
    unittest.main()
