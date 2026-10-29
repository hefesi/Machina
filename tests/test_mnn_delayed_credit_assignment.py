"""Tests for delayed reward credit assignment and recovery in the MNN."""
from __future__ import annotations

import unittest

from benchmarks.mnn_delayed_credit_assignment import run_benchmark


class MNNDelayedCreditAssignmentTests(unittest.TestCase):
    def test_delayed_reward_sign_decay_and_checkpoint_recovery(self):
        result = run_benchmark(max_delay_steps=8)

        self.assertTrue(result["passed"], result["criteria"])
        self.assertTrue(result["criteria"]["positive_reward_strengthens_eligible_connection"])
        self.assertTrue(result["criteria"]["negative_reward_weakens_eligible_connection"])
        self.assertTrue(result["criteria"]["longer_delay_attenuates_credit"])
        self.assertTrue(result["criteria"]["checkpoint_preserves_pending_episode"])
        self.assertTrue(result["criteria"]["traces_clear_after_resolution"])

    def test_rejects_invalid_delay_limit(self):
        for value in (0, 51, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                run_benchmark(max_delay_steps=value)


if __name__ == "__main__":
    unittest.main()
