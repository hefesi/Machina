import tempfile
import unittest
from pathlib import Path

from machina.causal_learning import CausalExperimentStore


class CausalExperimentStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = CausalExperimentStore(Path(self.tmp.name) / "causal.sqlite3")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _register(self, design="randomized"):
        return self.store.register_experiment(
            "retrieval-v1", design=design,
            treatment_name="new_retrieval_strategy",
            control_name="baseline_strategy",
            protocol_ref="protocol:retrieval-v1",
        )

    def test_randomized_comparison_estimates_group_effect_after_minimum_sample(self):
        self._register()
        for index in range(6):
            self.store.record_trial("retrieval-v1", "treatment", .8, evidence_ref=f"e-t-{index}", trial_id=f"t-{index}")
            self.store.record_trial("retrieval-v1", "control", .5, evidence_ref=f"e-c-{index}", trial_id=f"c-{index}")
        report = self.store.report("retrieval-v1")
        self.assertEqual("randomized_comparison", report["classification"])
        self.assertAlmostEqual(.3, report["estimate"]["effect"])
        self.assertEqual(6, report["treatment"]["n"])
        self.assertIn("individual counterfactual", report["estimate"]["counterfactual_scope"])

    def test_randomized_comparison_is_not_claimed_with_small_sample(self):
        self._register()
        self.store.record_trial("retrieval-v1", "treatment", .9, evidence_ref="e1", trial_id="t1")
        self.store.record_trial("retrieval-v1", "control", .1, evidence_ref="e2", trial_id="c1")
        report = self.store.report("retrieval-v1")
        self.assertEqual("insufficient_evidence", report["classification"])
        self.assertIsNone(report["estimate"])

    def test_observational_data_never_becomes_causal_estimate(self):
        self._register("observational")
        for index in range(6):
            self.store.record_trial("retrieval-v1", "treatment", .9, evidence_ref=f"et{index}", trial_id=f"t{index}")
            self.store.record_trial("retrieval-v1", "control", .2, evidence_ref=f"ec{index}", trial_id=f"c{index}")
        report = self.store.report("retrieval-v1")
        self.assertEqual("observational_association", report["classification"])
        self.assertIsNone(report["estimate"])

    def test_matched_comparison_uses_complete_pairs_only(self):
        self._register("matched")
        for index in range(6):
            self.store.record_trial("retrieval-v1", "treatment", .8, evidence_ref=f"et{index}", trial_id=f"t{index}", context_key=f"ctx{index}")
            self.store.record_trial("retrieval-v1", "control", .5, evidence_ref=f"ec{index}", trial_id=f"c{index}", context_key=f"ctx{index}")
        report = self.store.report("retrieval-v1")
        self.assertEqual("matched_comparison", report["classification"])
        self.assertEqual(6, report["estimate"]["matched_pairs"])
        self.assertAlmostEqual(.3, report["estimate"]["effect"])

    def test_matched_trials_require_context_and_reject_duplicate_arm(self):
        self._register("matched")
        with self.assertRaisesRegex(ValueError, "context_key"):
            self.store.record_trial("retrieval-v1", "treatment", .8, evidence_ref="e1", trial_id="t1")
        self.store.record_trial("retrieval-v1", "treatment", .8, evidence_ref="e2", trial_id="t2", context_key="same")
        with self.assertRaisesRegex(ValueError, "already has"):
            self.store.record_trial("retrieval-v1", "treatment", .7, evidence_ref="e3", trial_id="t3", context_key="same")

    def test_duplicate_trial_id_and_invalid_outcomes_are_rejected(self):
        self._register()
        with self.assertRaisesRegex(ValueError, "between 0 and 1"):
            self.store.record_trial("retrieval-v1", "treatment", 1.1, evidence_ref="e1", trial_id="t1")
        self.store.record_trial("retrieval-v1", "treatment", .7, evidence_ref="e1", trial_id="t1")
        with self.assertRaisesRegex(ValueError, "already been recorded"):
            self.store.record_trial("retrieval-v1", "control", .6, evidence_ref="e2", trial_id="t1")

    def test_duplicate_experiment_and_unknown_experiment_are_rejected(self):
        self._register()
        with self.assertRaisesRegex(ValueError, "already been registered"):
            self._register()
        with self.assertRaisesRegex(ValueError, "unknown"):
            self.store.report("missing")

    def test_report_threshold_must_be_at_least_two(self):
        self._register()
        with self.assertRaisesRegex(ValueError, "minimum_per_arm"):
            self.store.report("retrieval-v1", minimum_per_arm=1)


if __name__ == "__main__":
    unittest.main()
