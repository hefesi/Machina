from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from examples.machina_prototype import MachinaPrototype


class AutonomyPrototypeFeedbackTests(unittest.TestCase):
    def test_goal_feedback_survives_prototype_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            with MachinaPrototype(directory) as machina:
                result = machina.autonomy_step()
                self.assertEqual("goal_executed_in_prototype", result["status"])
                feedback = machina.autonomy_memory.record_feedback("success")
                self.assertEqual("success", feedback["outcome"])
                self.assertEqual(1, machina.status()["autonomy"]["successes"])

            with MachinaPrototype(directory) as restarted:
                status = restarted.status()["autonomy"]
                self.assertEqual(1, status["goals_recorded"])
                self.assertEqual(1, status["successes"])
                self.assertGreater(
                    status["drive_adjustments"][feedback["drive"]], 0
                )


if __name__ == "__main__":
    unittest.main()
