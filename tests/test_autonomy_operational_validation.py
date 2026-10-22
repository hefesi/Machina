from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from examples.autonomy_operational_demo import run_demo


class OperationalAutonomyValidationTests(unittest.TestCase):
    def test_feedback_changes_choice_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            # The demo owns an isolated temporary SQLite database. This test
            # asserts the externally observable result rather than implementation details.
            result = run_demo()
        self.assertTrue(result["passed"], result)
        self.assertEqual("strategy_a", result["baseline_selected"])
        self.assertEqual("strategy_b", result["selected_after_feedback_and_restart"])
        self.assertEqual(4, result["recorded_outcomes"]["successes"])


if __name__ == "__main__":
    unittest.main()
