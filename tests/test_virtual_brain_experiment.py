from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.brain import VirtualBrain
from machina.experiment_harness import ExperimentHarness, ExperimentSpec
from machina.virtual_brain_experiment import run_virtual_brain_trial


class VirtualBrainExperimentTests(unittest.TestCase):
    def make_spec(self, experiment_id: str, condition: str) -> ExperimentSpec:
        return ExperimentSpec(
            experiment_id=experiment_id,
            hypothesis_id="H1-global-workspace",
            condition=condition,
            seed=17,
            input_data={
                "observation": "A controlled observation for integration testing.",
                "objective": "Record and evaluate the observation.",
            },
            configuration={"workspace": condition},
            code_revision="test-revision",
            budget={"cycles": 1, "actions": 1},
        )

    def test_trial_executes_real_virtual_brain_and_records_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            brain = VirtualBrain(Path(directory) / "brain.sqlite")
            record = run_virtual_brain_trial(
                ExperimentHarness(), self.make_spec("real-brain-001", "baseline"), brain
            )
            self.assertEqual("completed", record.outcome["cycle_status"])
            self.assertEqual([], record.outcome["audit_errors"])
            self.assertEqual(1.0, record.metrics["cycle_completed"])
            self.assertEqual(1.0, record.metrics["audit_valid"])
            self.assertGreater(record.metrics["event_count"], 0)
            self.assertEqual(
                "DeterministicCognition",
                record.outcome["runtime_components"]["cognition"],
            )
            self.assertIn("cycle.completed", record.outcome["event_types"])
            brain.close()

    def test_trial_requires_observation_and_objective(self):
        with tempfile.TemporaryDirectory() as directory:
            brain = VirtualBrain(Path(directory) / "brain.sqlite")
            spec = ExperimentSpec(
                experiment_id="invalid-input",
                hypothesis_id="H1",
                condition="baseline",
                seed=1,
                input_data={"observation": "Only an observation"},
                configuration={},
                code_revision="test",
                budget={},
            )
            with self.assertRaisesRegex(ValueError, "objective"):
                run_virtual_brain_trial(ExperimentHarness(), spec, brain)
            brain.close()

    def test_repeated_trial_id_does_not_execute_second_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            brain = VirtualBrain(Path(directory) / "brain.sqlite")
            harness = ExperimentHarness()
            spec = self.make_spec("real-brain-idempotent", "baseline")
            first = run_virtual_brain_trial(harness, spec, brain)
            second = run_virtual_brain_trial(harness, spec, brain)
            self.assertIs(first, second)
            self.assertEqual(22, len(brain.store.all_events()))
            brain.close()


if __name__ == "__main__":
    unittest.main()
