from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.continuity_experiment import run_interruption_resume_trial
from machina.experiment_harness import ExperimentHarness, ExperimentSpec


class InterruptionResumeExperimentTests(unittest.TestCase):
    def make_spec(self):
        return ExperimentSpec(
            experiment_id="continuity-restart-001",
            hypothesis_id="H4-functional-continuity",
            condition="restart-at-memory-retrieved",
            seed=23,
            input_data={
                "observation": "A persistent observation across restart.",
                "objective": "Complete the same cognitive cycle after restart.",
            },
            configuration={"checkpoint": "workspace.updated"},
            code_revision="test-revision",
            budget={"cycles": 1, "restarts": 1},
        )

    def test_cycle_resumes_after_database_reopen_without_duplicate_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            record = run_interruption_resume_trial(
                ExperimentHarness(),
                self.make_spec(),
                Path(directory) / "continuity.sqlite",
            )
            self.assertEqual("cycle.completed", record.outcome["event_types"][-1])
            self.assertEqual(1.0, record.metrics["checkpoint_reached"])
            self.assertGreater(record.metrics["events_persisted_before_restart"], 0)
            self.assertEqual(1.0, record.metrics["audit_valid"])
            self.assertEqual(1.0, record.metrics["cycle_completed"])
            self.assertEqual(1.0, record.metrics["completion_event_exactly_once"])
            self.assertTrue(record.outcome["integrity_verified"])

    def test_rejects_missing_cycle_inputs(self):
        invalid = ExperimentSpec(
            experiment_id="continuity-invalid",
            hypothesis_id="H4",
            condition="restart",
            seed=1,
            input_data={"observation": "missing objective"},
            configuration={},
            code_revision="test",
            budget={"cycles": 1},
        )
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "objective"):
                run_interruption_resume_trial(
                    ExperimentHarness(), invalid, Path(directory) / "invalid.sqlite"
                )


if __name__ == "__main__":
    unittest.main()
