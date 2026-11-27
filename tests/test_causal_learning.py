import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from machina.causal_learning import CausalExperimentStore
from machina.contracts import Artifact, ContractKind, EpistemicStatus
from machina.event_store import EventStore
from machina.mnn_strategy_event_bridge import MNNStrategyEventBridge


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
            treatment_name="retrieve",
            control_name="archive",
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

    def test_confirmed_strategy_events_project_idempotently_into_causal_trials(self):
        with tempfile.TemporaryDirectory() as directory:
            event_store = EventStore(Path(directory) / "events.sqlite3")
            cycle_id = "cycle-causal-projection"
            event_store.create_cycle(cycle_id)
            bridge = MNNStrategyEventBridge(event_store)
            bridge.record_proposal(
                cycle_id,
                {"status": "proposed", "action": "retrieve", "context": "same task", "evidence_ids": ["obs-1"]},
                expected_reward=0.6,
                proposal_id="proposal-1",
            )
            outcome = bridge.record_outcome(
                cycle_id,
                "proposal-1",
                execution_confirmed=True,
                executed_action="retrieve",
                observed_reward=0.9,
                operation_id="operation-1",
            )
            self._register("randomized")
            projected = self.store.record_strategy_outcome(
                "retrieval-v1", "treatment", outcome
            )
            replayed = self.store.record_strategy_outcome(
                "retrieval-v1", "treatment", outcome
            )
            self.assertEqual(projected, replayed)
            self.assertEqual(1, self.store.report("retrieval-v1")["treatment"]["n"])
            self.assertEqual(outcome.artifact.id, projected["evidence_ref"])
            with self.assertRaisesRegex(ValueError, "does not match the experiment arm"):
                self.store.record_strategy_outcome(
                    "retrieval-v1", "control", outcome
                )
            self.assertEqual(0, self.store.report("retrieval-v1")["control"]["n"])

            bridge.record_proposal(
                cycle_id,
                {"status": "proposed", "action": "archive", "context": "same task", "evidence_ids": ["obs-2"]},
                expected_reward=0.5,
                proposal_id="proposal-2",
            )
            control_outcome = bridge.record_outcome(
                cycle_id,
                "proposal-2",
                execution_confirmed=True,
                executed_action="archive",
                observed_reward=0.4,
                operation_id="operation-2",
            )
            control_trial = self.store.record_strategy_outcome(
                "retrieval-v1", "control", control_outcome
            )
            self.assertEqual("control", control_trial["arm"])
            self.assertEqual(1, self.store.report("retrieval-v1")["control"]["n"])
            event_store.close()

    def test_concurrent_confirmed_strategy_outcome_projection_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            event_store = EventStore(Path(directory) / "events.sqlite3")
            try:
                cycle_id = "cycle-causal-concurrent-projection"
                event_store.create_cycle(cycle_id)
                bridge = MNNStrategyEventBridge(event_store)
                bridge.record_proposal(
                    cycle_id,
                    {"status": "proposed", "action": "retrieve", "context": "same task", "evidence_ids": ["obs-concurrent"]},
                    expected_reward=0.6,
                    proposal_id="proposal-concurrent",
                )
                outcome = bridge.record_outcome(
                    cycle_id,
                    "proposal-concurrent",
                    execution_confirmed=True,
                    executed_action="retrieve",
                    observed_reward=0.9,
                    operation_id="operation-concurrent",
                )
                self._register("randomized")
                database = Path(self.tmp.name) / "causal.sqlite3"
                barrier = threading.Barrier(4)

                def project(_):
                    # Each worker owns its SQLite connection. The barrier makes
                    # independent callers contend for the same operation ID.
                    store = CausalExperimentStore(database)
                    try:
                        barrier.wait(timeout=5)
                        return store.record_strategy_outcome(
                            "retrieval-v1", "treatment", outcome
                        )
                    finally:
                        store.close()

                with ThreadPoolExecutor(max_workers=4) as executor:
                    results = list(executor.map(project, range(4)))

                self.assertTrue(all(item == results[0] for item in results[1:]))
                self.assertEqual(1, self.store.report("retrieval-v1")["treatment"]["n"])
            finally:
                event_store.close()

    def test_matched_strategy_outcomes_require_the_recorded_context(self):
        with tempfile.TemporaryDirectory() as directory:
            event_store = EventStore(Path(directory) / "events.sqlite3")
            cycle_id = "cycle-matched-context"
            event_store.create_cycle(cycle_id)
            bridge = MNNStrategyEventBridge(event_store)
            self._register("matched")

            bridge.record_proposal(
                cycle_id,
                {"status": "proposed", "action": "retrieve", "context": " Task   A ", "evidence_ids": ["obs-t"]},
                expected_reward=0.6,
                proposal_id="matched-treatment",
            )
            treatment_outcome = bridge.record_outcome(
                cycle_id,
                "matched-treatment",
                execution_confirmed=True,
                executed_action="retrieve",
                observed_reward=0.9,
                operation_id="matched-operation-treatment",
            )
            with self.assertRaisesRegex(ValueError, "must match the recorded strategy outcome context"):
                self.store.record_strategy_outcome(
                    "retrieval-v1", "treatment", treatment_outcome, context_key="task b"
                )
            self.assertEqual([], self.store.report("retrieval-v1")["trials"])

            projected_treatment = self.store.record_strategy_outcome(
                "retrieval-v1", "treatment", treatment_outcome, context_key="task a"
            )
            self.assertEqual("task a", projected_treatment["context_key"])

            bridge.record_proposal(
                cycle_id,
                {"status": "proposed", "action": "archive", "context": "TASK A", "evidence_ids": ["obs-c"]},
                expected_reward=0.5,
                proposal_id="matched-control",
            )
            control_outcome = bridge.record_outcome(
                cycle_id,
                "matched-control",
                execution_confirmed=True,
                executed_action="archive",
                observed_reward=0.4,
                operation_id="matched-operation-control",
            )
            projected_control = self.store.record_strategy_outcome(
                "retrieval-v1", "control", control_outcome, context_key="task a"
            )
            self.assertEqual("task a", projected_control["context_key"])
            self.assertEqual(
                ["task a", "task a"],
                [trial["context_key"] for trial in self.store.report("retrieval-v1")["trials"]],
            )
            event_store.close()

    def test_unconfirmed_or_non_strategy_events_cannot_be_projected(self):
        self._register()
        wrong = object()
        with self.assertRaisesRegex(ValueError, "strategy.outcome.recorded"):
            self.store.record_strategy_outcome("retrieval-v1", "treatment", wrong)

    def test_report_threshold_must_be_at_least_two(self):
        self._register()
        with self.assertRaisesRegex(ValueError, "minimum_per_arm"):
            self.store.report("retrieval-v1", minimum_per_arm=1)

    def test_randomized_report_uses_welch_student_t_interval_for_small_samples(self):
        self._register("randomized")
        treatment = [.6, .7, .8, .9, 1.0]
        control = [.1, .2, .3, .4, .5]
        for index, (treated, controlled) in enumerate(zip(treatment, control)):
            self.store.record_trial(
                "retrieval-v1", "treatment", treated,
                evidence_ref=f"welch-t-{index}", trial_id=f"welch-tt-{index}",
            )
            self.store.record_trial(
                "retrieval-v1", "control", controlled,
                evidence_ref=f"welch-c-{index}", trial_id=f"welch-ct-{index}",
            )

        report = self.store.report("retrieval-v1")
        self.assertEqual("randomized_comparison", report["classification"])
        estimate = report["estimate"]
        self.assertEqual("student_t_welch", estimate["interval_method"])
        self.assertEqual("available", estimate["interval_status"])
        self.assertAlmostEqual(8.0, estimate["degrees_of_freedom"])
        self.assertAlmostEqual(2.306, estimate["critical_value"], places=3)
        self.assertGreater(estimate["critical_value"], 1.96)
        self.assertEqual(
            estimate["confidence_interval_95_student_t"],
            estimate["confidence_interval_95_normal_approx"],
        )

    def test_matched_report_uses_paired_student_t_interval(self):
        self._register("matched")
        differences = [.1, .2, .3, .4, .5]
        for index, difference in enumerate(differences):
            self.store.record_trial(
                "retrieval-v1", "control", .4,
                evidence_ref=f"paired-c-{index}", trial_id=f"paired-ct-{index}",
                context_key=f"paired-{index}",
            )
            self.store.record_trial(
                "retrieval-v1", "treatment", .4 + difference,
                evidence_ref=f"paired-t-{index}", trial_id=f"paired-tt-{index}",
                context_key=f"paired-{index}",
            )

        estimate = self.store.report("retrieval-v1")["estimate"]
        self.assertEqual("student_t_paired", estimate["interval_method"])
        self.assertEqual(4.0, estimate["degrees_of_freedom"])
        self.assertAlmostEqual(2.776, estimate["critical_value"], places=3)
        self.assertIsNotNone(estimate["confidence_interval_95_student_t"])

    def test_strategy_guidance_holds_when_empirical_variance_is_zero(self):
        self._register("randomized")
        for index in range(12):
            self.store.record_trial(
                "retrieval-v1", "treatment", .9,
                evidence_ref=f"constant-t-{index}", trial_id=f"constant-tt-{index}",
            )
            self.store.record_trial(
                "retrieval-v1", "control", .2,
                evidence_ref=f"constant-c-{index}", trial_id=f"constant-ct-{index}",
            )

        report = self.store.report("retrieval-v1")
        self.assertEqual(
            "unavailable_zero_estimated_variance",
            report["estimate"]["interval_status"],
        )
        self.assertIsNone(report["estimate"]["confidence_interval_95_student_t"])
        guidance = self.store.strategy_guidance("retrieval-v1")
        self.assertEqual("hold", guidance["guidance"])
        self.assertEqual(
            "uncertainty_interval_unavailable_due_to_zero_estimated_variance",
            guidance["reason"],
        )

    def test_matched_strategy_guidance_holds_when_paired_variance_is_zero(self):
        self._register("matched")
        for index in range(5):
            context = f"constant-pair-{index}"
            self.store.record_trial(
                "retrieval-v1", "control", .2,
                evidence_ref=f"matched-constant-c-{index}",
                trial_id=f"matched-constant-ct-{index}",
                context_key=context,
            )
            self.store.record_trial(
                "retrieval-v1", "treatment", .9,
                evidence_ref=f"matched-constant-t-{index}",
                trial_id=f"matched-constant-tt-{index}",
                context_key=context,
            )

        report = self.store.report("retrieval-v1")
        self.assertEqual("matched_comparison", report["classification"])
        self.assertEqual(
            "unavailable_zero_estimated_variance",
            report["estimate"]["interval_status"],
        )
        guidance = self.store.strategy_guidance("retrieval-v1")
        self.assertEqual("hold", guidance["guidance"])

    def test_strategy_guidance_only_recommends_when_interval_excludes_zero(self):
        self._register("randomized")
        for index in range(20):
            treatment = .85 + (index % 5) * .01
            control = .20 + (index % 5) * .01
            self.store.record_trial("retrieval-v1", "treatment", treatment, evidence_ref=f"et{index}", trial_id=f"gt{index}")
            self.store.record_trial("retrieval-v1", "control", control, evidence_ref=f"ec{index}", trial_id=f"gc{index}")
        guidance = self.store.strategy_guidance("retrieval-v1")
        self.assertEqual("favor_treatment_for_human_review", guidance["guidance"])
        self.assertFalse(guidance["policy_mutated"])
        self.assertTrue(guidance["requires_human_or_external_policy_approval"])

    def test_strategy_guidance_holds_for_observational_or_insufficient_data(self):
        self._register("observational")
        for index in range(6):
            self.store.record_trial("retrieval-v1", "treatment", .9, evidence_ref=f"ot{index}", trial_id=f"ot{index}")
            self.store.record_trial("retrieval-v1", "control", .2, evidence_ref=f"oc{index}", trial_id=f"oc{index}")
        guidance = self.store.strategy_guidance("retrieval-v1")
        self.assertEqual("hold", guidance["guidance"])
        self.assertEqual("observational_data_cannot_authorize_policy_changes", guidance["reason"])


if __name__ == "__main__":
    unittest.main()
