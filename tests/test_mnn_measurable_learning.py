"""Regression tests for measurable MNN learning and restart adaptation."""
from __future__ import annotations

import unittest

from benchmarks.mnn_persistent_adaptation import run_benchmark


class MNNMeasurableLearningTests(unittest.TestCase):
    def test_learns_reward_mapping_adapts_after_reversal_and_survives_restart(self):
        result = run_benchmark(rounds_per_phase=20)

        self.assertTrue(result["passed"], result)
        self.assertGreaterEqual(result["phase_1"]["last_10_reward_rate"], 0.8)
        self.assertGreaterEqual(result["phase_2"]["last_10_reward_rate"], 0.8)
        self.assertGreater(
            result["phase_1"]["predictions"]["left"],
            result["phase_1"]["predictions"]["right"],
        )
        self.assertGreater(
            result["phase_2"]["predictions"]["right"],
            result["phase_2"]["predictions"]["left"],
        )
        self.assertTrue(result["restart"]["learner_state_preserved"])
        self.assertTrue(result["persistent_memory"]["environment_shift_recalled"])
        self.assertEqual(result["persistent_memory"]["archive_count_after_reopen"], 2)


if __name__ == "__main__":
    unittest.main()
