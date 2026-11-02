from __future__ import annotations

import json
import unittest

from machina.experiment_harness import ExperimentHarness, ExperimentSpec


def make_spec(
    experiment_id: str,
    condition: str,
    *,
    seed: int = 7,
    input_data: dict | None = None,
    budget: dict | None = None,
) -> ExperimentSpec:
    return ExperimentSpec(
        experiment_id=experiment_id,
        hypothesis_id="H1-global-workspace",
        condition=condition,
        seed=seed,
        input_data=input_data or {"cue": "distributed-evidence"},
        configuration={"workspace_enabled": condition != "local"},
        code_revision="abc123",
        budget=budget or {"steps": 20, "tokens": 1000},
    )


class ExperimentHarnessTests(unittest.TestCase):
    def test_records_reproducible_trial_and_exports_jsonl(self):
        harness = ExperimentHarness()
        spec = make_spec("trial-1", "local")
        record = harness.run(
            spec,
            lambda _: {"metrics": {"accuracy": 0.75}, "notes": "baseline"},
        )
        self.assertEqual(64, len(record.record_hash))
        payload = json.loads(harness.to_jsonl())
        self.assertEqual("trial-1", payload["spec"]["experiment_id"])
        self.assertEqual(0.75, payload["metrics"]["accuracy"])
        self.assertEqual(1, len(harness.records))

    def test_duplicate_id_is_idempotent_and_does_not_execute_again(self):
        harness = ExperimentHarness()
        spec = make_spec("trial-2", "local")
        calls = []
        first = harness.run(spec, lambda _: calls.append("called") or {"metrics": {"score": 1}})
        second = harness.run(spec, lambda _: calls.append("called-again") or {"metrics": {"score": 9}})
        self.assertIs(first, second)
        self.assertEqual(["called"], calls)

    def test_duplicate_id_with_different_spec_is_rejected(self):
        harness = ExperimentHarness()
        harness.run(make_spec("trial-3", "local"), lambda _: {"metrics": {"score": 1}})
        with self.assertRaisesRegex(ValueError, "different specification"):
            harness.run(make_spec("trial-3", "integrated"), lambda _: {"metrics": {"score": 1}})

    def test_paired_comparison_requires_same_seed_input_and_budget(self):
        harness = ExperimentHarness()
        baseline = make_spec("baseline", "local")
        treatment = make_spec("treatment", "integrated")
        harness.run(baseline, lambda _: {"metrics": {"accuracy": 0.6}})
        harness.run(treatment, lambda _: {"metrics": {"accuracy": 0.8}})
        comparison = harness.compare("baseline", "treatment", "accuracy")
        self.assertAlmostEqual(0.2, comparison["delta_treatment_minus_baseline"])
        self.assertEqual("descriptive_only", comparison["interpretation"])

        mismatched = make_spec("mismatch", "integrated", seed=8)
        harness.run(mismatched, lambda _: {"metrics": {"accuracy": 0.9}})
        with self.assertRaisesRegex(ValueError, "same seed"):
            harness.compare("baseline", "mismatch", "accuracy")

    def test_rejects_invalid_metrics_and_non_json_outcomes(self):
        harness = ExperimentHarness()
        with self.assertRaisesRegex(ValueError, "finite"):
            harness.run(make_spec("nan", "local"), lambda _: {"metrics": {"score": float("nan")}})
        with self.assertRaisesRegex(ValueError, "JSON-compatible"):
            harness.run(make_spec("object", "local"), lambda _: {"details": object()})

    def test_spec_rejects_invalid_seed_and_budget(self):
        with self.assertRaisesRegex(ValueError, "seed"):
            make_spec("bad-seed", "local", seed=True)
        with self.assertRaisesRegex(ValueError, "budget"):
            make_spec("bad-budget", "local", budget={"steps": -1})


if __name__ == "__main__":
    unittest.main()
