from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_compositional_transfer import run_benchmark


class MNNCompositionalTransferTests(unittest.TestCase):
    def test_unseen_feature_combinations_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark(checkpoint_path=Path(directory) / "composition.json")
        self.assertTrue(result["passed"], result)
        self.assertEqual(0.5, result["fixed_weights_baseline"]["accuracy"])
        self.assertEqual(1.0, result["trained_network"]["accuracy"])
        self.assertEqual(1.0, result["checkpoint_restored_network"]["accuracy"])
        self.assertEqual(result["trained_weights"], result["restored_weights"])
        self.assertEqual(
            result["trained_network"]["predictions"],
            result["checkpoint_restored_network"]["predictions"],
        )

    def test_invalid_learning_rates_are_rejected(self):
        for rate in (0, -0.1, float("nan"), float("inf")):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    run_benchmark(learning_rate=rate)


if __name__ == "__main__":
    unittest.main()
