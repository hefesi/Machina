from __future__ import annotations

import tempfile
import unittest

from examples.machina_prototype import MachinaPrototype


class AutonomyPrototypeFeedbackTests(unittest.TestCase):
    def test_goal_feedback_survives_prototype_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            with MachinaPrototype(directory) as machina:
                result = machina.autonomy_step()
                self.assertEqual("goal_executed_in_prototype", result["status"])
                persistent_id = result["persistent_goal"]["id"]
                feedback = machina.record_goal_feedback("success", "Verified by test")
                self.assertEqual("success", feedback["feedback_recorded"]["outcome"])
                self.assertEqual("completed", feedback["persistent_goal"]["status"])
                self.assertEqual(persistent_id, feedback["persistent_goal"]["id"])
                self.assertEqual(1, machina.status()["autonomy"]["successes"])

            with MachinaPrototype(directory) as restarted:
                status = restarted.status()
                self.assertEqual(1, status["autonomy"]["goals_recorded"])
                self.assertEqual(1, status["autonomy"]["successes"])
                self.assertEqual(1, status["persistent_goals"]["completed"])
                self.assertGreater(
                    status["autonomy"]["drive_adjustments"][feedback["feedback_recorded"]["drive"]], 0
                )
                goals = restarted.goal_store.list_goals("completed")
                self.assertEqual("Verified by test", goals[0]["evidence"])


if __name__ == "__main__":
    unittest.main()
