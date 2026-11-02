from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.brain import VirtualBrain
from machina.experiment_harness import ExperimentHarness
from machina.experiment_protocol import run_paired_conditions


class PairedExperimentProtocolTests(unittest.TestCase):
    def test_runs_paired_real_brains_with_equal_inputs_and_budgets(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []

            def factory(condition, seed, configuration):
                calls.append((condition, seed, dict(configuration)))
                path = Path(directory) / f"{condition}-{seed}.sqlite"
                return VirtualBrain(path)

            report = run_paired_conditions(
                harness=ExperimentHarness(),
                hypothesis_id="H1-workspace",
                baseline_condition="local",
                treatment_condition="shared",
                seeds=(11, 29),
                input_data={"observation": "same evidence", "objective": "evaluate evidence"},
                baseline_configuration={"workspace": "local"},
                treatment_configuration={"workspace": "shared"},
                code_revision="test-revision",
                budget={"cycles": 1, "actions": 1},
                brain_factory=factory,
                metrics=("cycle_completed", "audit_valid"),
            )

            self.assertEqual(4, len(calls))
            self.assertEqual([11, 29], report["seeds"])
            self.assertEqual(4, len(report["comparisons"]))
            self.assertTrue(all(
                item["interpretation"] == "descriptive_only"
                for item in report["comparisons"]
            ))
            self.assertEqual(
                ["H1-workspace:local:seed-11", "H1-workspace:local:seed-29"],
                report["conditions"]["local"]["trial_ids"],
            )

    def test_rejects_mismatched_virtual_brain_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "cycles=1"):
                run_paired_conditions(
                    harness=ExperimentHarness(),
                    hypothesis_id="H1",
                    baseline_condition="base",
                    treatment_condition="treatment",
                    seeds=(1,),
                    input_data={"observation": "x", "objective": "y"},
                    baseline_configuration={},
                    treatment_configuration={},
                    code_revision="test",
                    budget={"cycles": 2},
                    brain_factory=lambda *_: VirtualBrain(Path(directory) / "brain.sqlite"),
                    metrics=("audit_valid",),
                )


if __name__ == "__main__":
    unittest.main()
