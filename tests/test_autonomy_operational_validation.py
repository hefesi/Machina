from __future__ import annotations

import unittest

from examples.autonomy_operational_demo import run_demo


class OperationalAutonomyValidationTests(unittest.TestCase):
    def test_feedback_changes_choice_and_survives_restart(self):
        result = run_demo()
        self.assertTrue(result["passed"], result)
        self.assertEqual("strategy_a", result["baseline_selected"])
        self.assertEqual("strategy_b", result["selected_after_feedback_and_restart"])
        self.assertEqual(4, result["recorded_outcomes"]["successes"])


if __name__ == "__main__":
    unittest.main()
