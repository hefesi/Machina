from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_generalization import HELD_OUT_INPUTS, run_benchmark


class MNNTransferTests(unittest.TestCase):
    def test_held_out_inputs_and_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark(checkpoint_path=Path(directory) / "model.json")
        self.assertTrue(result["passed"], result)
        self.assertEqual(0.5, result["fixed_weights_baseline"]["accuracy"])
        self.assertEqual(1.0, result["trained_network"]["accuracy"])
        self.assertEqual(1.0, result["checkpoint_restored_network"]["accuracy"])
        self.assertEqual(result["trained_weights"], result["restored_weights"])
        self.assertTrue(all(value not in (-1.0, 1.0) for value in HELD_OUT_INPUTS))

    def test_invalid_learning_rates(self):
        for rate in (0, float("nan"), float("inf"), -0.1):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    run_benchmark(learning_rate=rate)


if __name__ == "__main__":
    unittest.main()
