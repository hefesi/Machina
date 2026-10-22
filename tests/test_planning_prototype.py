from __future__ import annotations

import tempfile
import unittest

from examples.machina_prototype import MachinaPrototype


class PlanningPrototypeIntegrationTests(unittest.TestCase):
    def test_plan_is_created_from_persistent_goal_and_survives_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            with MachinaPrototype(directory) as machina:
                autonomy = machina.autonomy_step()
                self.assertEqual("goal_executed_in_prototype", autonomy["status"])
                goal_record_id = autonomy["persistent_goal"]["id"]
                plan = machina.create_plan(goal_record_id)
                self.assertEqual("active", plan["status"])
                self.assertGreaterEqual(len(plan["steps"]), 3)
                self.assertEqual(1, len(machina.plan_store.ready_steps(plan["id"])))
                first_step = machina.plan_store.ready_steps(plan["id"])[0]
                result = machina.plan_store.record_step_outcome(
                    plan["id"], first_step["step_id"], "success", "Explicit test evidence"
                )
                self.assertEqual("completed", result["steps"][0]["status"])
                plan_id = plan["id"]

            with MachinaPrototype(directory) as restarted:
                loaded = restarted.plan_store.get_plan(plan_id)
                self.assertEqual("active", loaded["status"])
                self.assertEqual("completed", loaded["steps"][0]["status"])
                self.assertEqual("Explicit test evidence", loaded["steps"][0]["evidence"])
                self.assertEqual(1, restarted.status()["plans"]["active"])


if __name__ == "__main__":
    unittest.main()
