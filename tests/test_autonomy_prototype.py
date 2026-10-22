from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from examples.machina_prototype import MachinaPrototype


class MachinaAutonomyIntegrationTests(unittest.TestCase):
    def test_autonomy_command_generates_goal_and_runs_auditable_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            with MachinaPrototype(Path(directory)) as machina:
                result = machina.autonomy_step()

                self.assertEqual("goal_executed_in_prototype", result["status"])
                selected = result["decision"]["selected_goal"]
                self.assertEqual("establish_memory_baseline", selected["goal_id"])
                self.assertEqual("completed", result["cycle"]["status"])
                self.assertTrue(result["cycle"]["audit_valid"])
                self.assertIn("acknowledge-only executor", result["autonomy_scope"])


if __name__ == "__main__":
    unittest.main()
