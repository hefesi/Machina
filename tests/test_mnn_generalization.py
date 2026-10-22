"""Tests for held-out generalization and checkpoint retention."""
from __future__ import annotations

import unittest

from benchmarks.mnn_generalization import run_benchmark


class MNNGeneralizationBenchmarkTests(unittest.TestCase):
    def test_reward_learning_generalizes_and_survives_checkpoint(self) -> None:
        result = run_benchmark()
        self.assertTrue(result["generalization"]["passed"], result)
        self.assertTrue(result["retention"]["passed"], result)
        self.assertEqual(
            result["held_out"]["reward_learning"]["cases"],
            result["held_out"]["checkpoint_restored"]["cases"],
        )

    def test_training_contexts_do_not_include_held_out_context(self) -> None:
        result = run_benchmark()
        self.assertNotIn("a_and_b_unseen", result["training_contexts"])
        self.assertEqual(["a_and_b_unseen"], result["held_out_contexts"])

    def test_invalid_parameters_are_rejected(self) -> None:
        for rounds in (0, -1, True):
            with self.subTest(rounds=rounds):
                with self.assertRaises(ValueError):
                    run_benchmark(training_rounds=rounds)
        for rate in (-0.1, float("nan"), float("inf"), True):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    run_benchmark(learning_rate=rate)


if __name__ == "__main__":
    unittest.main()
