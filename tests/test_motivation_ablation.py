from __future__ import annotations

import unittest

from machina.autonomy import AutonomyContext
from machina.experiment_harness import ExperimentHarness
from machina.motivation_ablation import run_motivation_ablation


class MotivationAblationTests(unittest.TestCase):
    def test_persistent_drive_changes_internal_goal_selection(self):
        result = run_motivation_ablation(
            ExperimentHarness(),
            hypothesis_id="H-motivation-selection",
            code_revision="test-revision",
            context=AutonomyContext(),
            seed=11,
            drive_name="exploration",
            pressure=0.95,
        )
        off = result["trials"]["motivation_off"]
        on = result["trials"]["motivation_on"]
        self.assertEqual(0.0, off["metrics"]["motivational_goal_selected"])
        self.assertEqual(1.0, on["metrics"]["motivational_goal_selected"])
        self.assertEqual("inspect_internal_state", off["outcome"]["decision"]["selected_goal"]["goal_id"])
        self.assertEqual("sustain_drive:exploration", on["outcome"]["decision"]["selected_goal"]["goal_id"])
        self.assertEqual(1.0, result["comparison"]["delta_treatment_minus_baseline"])

    def test_rejects_invalid_pressure(self):
        with self.assertRaisesRegex(ValueError, "pressure"):
            run_motivation_ablation(
                ExperimentHarness(),
                hypothesis_id="H-motivation",
                code_revision="test",
                pressure=1.5,
            )


if __name__ == "__main__":
    unittest.main()
