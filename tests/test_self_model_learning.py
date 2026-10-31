import tempfile
import unittest
from pathlib import Path

from machina.autonomy import GoalCandidate
from machina.goal_outcome_learning import GoalOutcomeLearner
from machina.self_model import SelfModel
from machina.self_model_learning import SelfModelLearningBridge


class SelfModelLearningBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.learner = GoalOutcomeLearner(Path(self.tmp.name) / "outcomes.sqlite3")
        self.model = SelfModel()
        self.bridge = SelfModelLearningBridge(self.model, self.learner)

    def tearDown(self):
        self.learner.close()
        self.tmp.cleanup()

    def test_evaluated_history_updates_inferred_capability(self):
        self.learner.observe(
            "research", .9, evidence="Nine of ten acceptance checks passed.",
            observation_id="result-1",
        )
        result = self.bridge.update_capability(
            "research", capability_name="research_execution", cycle_id="cycle-12"
        )
        capability = result["self_model"]["capability_estimates"]["research_execution"]
        self.assertEqual("inferred", capability["status"])
        self.assertEqual("goal-outcome:1", capability["evidence_ref"])
        self.assertEqual(1, capability["estimate"]["observations"])
        self.assertEqual("goal-outcome:1", self.model.prediction_errors[0]["prediction_ref"])

    def test_cannot_infer_capability_without_evaluated_history(self):
        with self.assertRaisesRegex(ValueError, "without evaluated outcome"):
            self.bridge.update_capability("unknown_task", cycle_id="cycle-1")

    def test_bridge_does_not_claim_observed_capability(self):
        self.learner.observe("deployment", .5, evidence="Partial deployment result.")
        result = self.bridge.update_capability("deployment", cycle_id="cycle-2")
        self.assertEqual("inferred", result["status"])
        self.assertEqual("inferred", self.model.capability_estimates["deployment"]["status"])


    def test_prediction_calibration_updates_inferred_capability_after_minimum_sample(self):
        for index, matched in enumerate((True, True, False, True, False), start=1):
            self.model.predict("runtime", True, prediction_ref=f"p{index}", cycle_id="predict", confidence=0.8, horizon="short")
            self.model.evaluate_prediction(f"p{index}", True if matched else False, cycle_id="evaluate", evidence_ref=f"e{index}")
        result = self.bridge.update_prediction_calibration("runtime", cycle_id="cycle-calibration", horizon="short")
        capability = self.model.capability_estimates["runtime"]
        self.assertEqual("inferred", capability["status"])
        self.assertAlmostEqual(0.6, result["estimate"]["accuracy"])
        self.assertEqual(5, result["estimate"]["evaluated"])
        self.assertEqual("prediction-calibration:e1|e2|e3|e4|e5", result["evidence_ref"])
        self.assertAlmostEqual(1.0, capability["confidence"])

    def test_prediction_calibration_rejects_insufficient_history_without_mutation(self):
        self.model.predict("runtime", True, prediction_ref="p1", cycle_id="c1")
        self.model.evaluate_prediction("p1", True, cycle_id="c2", evidence_ref="e1")
        with self.assertRaisesRegex(ValueError, "insufficient evaluated predictions"):
            self.bridge.update_prediction_calibration("runtime", cycle_id="c3", min_evaluated=3)
        self.assertNotIn("runtime", self.model.capability_estimates)

    def test_prediction_calibration_rejects_low_coverage_without_mutation(self):
        for index in range(4):
            self.model.predict("runtime", True, prediction_ref=f"p{index}", cycle_id="c1")
        self.model.evaluate_prediction("p0", True, cycle_id="c2", evidence_ref="e0")
        self.model.evaluate_prediction("p1", True, cycle_id="c2", evidence_ref="e1")
        with self.assertRaisesRegex(ValueError, "coverage"):
            self.bridge.update_prediction_calibration("runtime", cycle_id="c3", min_evaluated=2, minimum_coverage=0.75)
        self.assertNotIn("runtime", self.model.capability_estimates)

    def test_prediction_calibration_validates_thresholds(self):
        with self.assertRaisesRegex(ValueError, "min_evaluated"):
            self.bridge.update_prediction_calibration("runtime", cycle_id="c1", min_evaluated=0)
        with self.assertRaisesRegex(ValueError, "minimum_coverage"):
            self.bridge.update_prediction_calibration("runtime", cycle_id="c1", minimum_coverage=1.5)



    def _causal_store(self, design="randomized", treatment=0.9, control=0.2, n=12, suffix=""):
        from machina.causal_learning import CausalExperimentStore
        store = CausalExperimentStore(Path(self.tmp.name) / ("causal-" + design + suffix + ".sqlite3"))
        store.register_experiment(
            "exp-1", design=design, treatment_name="new_strategy",
            control_name="baseline", protocol_ref="protocol:exp-1",
        )
        for index in range(n):
            if design == "matched":
                context = f"context-{index}"
                store.record_trial("exp-1", "treatment", treatment, evidence_ref=f"et-{index}", trial_id=f"t-{index}", context_key=context)
                store.record_trial("exp-1", "control", control, evidence_ref=f"ec-{index}", trial_id=f"c-{index}", context_key=context)
            else:
                store.record_trial("exp-1", "treatment", treatment, evidence_ref=f"et-{index}", trial_id=f"t-{index}")
                store.record_trial("exp-1", "control", control, evidence_ref=f"ec-{index}", trial_id=f"c-{index}")
        return store

    def test_randomized_causal_experiment_updates_inferred_belief_with_provenance(self):
        store = self._causal_store()
        try:
            result = self.bridge.update_belief_from_causal_experiment(
                store, "exp-1", belief_property="retrieval_strategy_effect",
                cycle_id="cycle-causal",
            )
            belief = self.model.beliefs["retrieval_strategy_effect"]
            self.assertTrue(result["accepted"])
            self.assertEqual("inferred", belief["status"])
            self.assertEqual("randomized_comparison", belief["value"]["classification"])
            self.assertGreater(belief["value"]["effect_treatment_minus_control"], 0)
            self.assertIn("protocol:exp-1", str(belief["value"]["protocol_ref"]))
            self.assertIn("et-0", belief["evidence_ref"])
            self.assertEqual("cycle-causal", belief["observed_at_cycle"])
        finally:
            store.close()

    def test_matched_causal_experiment_can_update_inferred_belief(self):
        store = self._causal_store(design="matched")
        try:
            result = self.bridge.update_belief_from_causal_experiment(
                store, "exp-1", belief_property="matched_effect", cycle_id="cycle-matched",
            )
            self.assertTrue(result["accepted"])
            self.assertEqual("matched_comparison", self.model.beliefs["matched_effect"]["value"]["classification"])
        finally:
            store.close()

    def test_causal_bridge_rejects_interval_crossing_zero_without_mutation(self):
        from machina.causal_learning import CausalExperimentStore
        store = CausalExperimentStore(Path(self.tmp.name) / "causal-uncertain.sqlite3")
        store.register_experiment(
            "exp-1", design="randomized", treatment_name="new_strategy",
            control_name="baseline", protocol_ref="protocol:uncertain",
        )
        for index in range(12):
            treatment = 0.9 if index % 2 == 0 else 0.1
            store.record_trial("exp-1", "treatment", treatment, evidence_ref=f"et-{index}", trial_id=f"t-{index}")
            store.record_trial("exp-1", "control", 0.5, evidence_ref=f"ec-{index}", trial_id=f"c-{index}")
        try:
            result = self.bridge.update_belief_from_causal_experiment(
                store, "exp-1", belief_property="uncertain_effect", cycle_id="cycle-reject",
            )
            self.assertFalse(result["accepted"])
            self.assertIn("interval does not exclude zero", result["reason"])
            self.assertFalse(result["self_model_updated"])
            self.assertNotIn("uncertain_effect", self.model.beliefs)
        finally:
            store.close()

    def test_new_causal_evidence_revises_belief_and_marks_opposite_effect(self):
        first = self._causal_store(treatment=0.9, control=0.2, suffix="-first")
        second = self._causal_store(treatment=0.2, control=0.9, suffix="-second")
        try:
            self.bridge.update_belief_from_causal_experiment(
                first, 'exp-1', belief_property='strategy_effect', cycle_id='cycle-1',
            )
            result = self.bridge.update_belief_from_causal_experiment(
                second, 'exp-1', belief_property='strategy_effect', cycle_id='cycle-2',
            )
            self.assertTrue(result['accepted'])
            self.assertTrue(result['contradicts_previous'])
            self.assertEqual(1, len(self.model.belief_revision_history))
            revision = self.model.belief_revision_history[0]
            self.assertTrue(revision['contradicts_previous'])
            self.assertGreater(revision['previous']['value']['effect_treatment_minus_control'], 0)
            self.assertLess(revision['new']['value']['effect_treatment_minus_control'], 0)
            self.assertEqual('causal_experiment_bridge', revision['source'])
        finally:
            first.close()
            second.close()
    def test_causal_bridge_never_promotes_observational_association(self):
        store = self._causal_store(design="observational")
        try:
            result = self.bridge.update_belief_from_causal_experiment(
                store, "exp-1", belief_property="observed_association", cycle_id="cycle-observe",
            )
            self.assertFalse(result["accepted"])
            self.assertEqual("observational_association", result["classification"])
            self.assertNotIn("observed_association", self.model.beliefs)
        finally:
            store.close()

    def test_causal_bridge_is_idempotent_for_same_experiment_and_property(self):
        store = self._causal_store()
        try:
            first = self.bridge.update_belief_from_causal_experiment(
                store, "exp-1", belief_property="effect", cycle_id="cycle-1",
            )
            second = self.bridge.update_belief_from_causal_experiment(
                store, "exp-1", belief_property="effect", cycle_id="cycle-2",
            )
            self.assertTrue(first["self_model_updated"])
            self.assertTrue(second["already_applied"])
            self.assertFalse(second["self_model_updated"])
            self.assertEqual("cycle-1", self.model.cycle_id)
        finally:
            store.close()

    def test_causal_bridge_validates_thresholds_and_minimum_effect(self):
        store = self._causal_store()
        try:
            with self.assertRaisesRegex(ValueError, "minimum_per_arm"):
                self.bridge.update_belief_from_causal_experiment(
                    store, "exp-1", belief_property="effect", cycle_id="c", minimum_per_arm=1,
                )
            with self.assertRaisesRegex(ValueError, "minimum_effect"):
                self.bridge.update_belief_from_causal_experiment(
                    store, "exp-1", belief_property="effect", cycle_id="c", minimum_effect=float("nan"),
                )
            rejected = self.bridge.update_belief_from_causal_experiment(
                store, "exp-1", belief_property="tiny_effect", cycle_id="c", minimum_effect=0.9,
            )
            self.assertFalse(rejected["accepted"])
            self.assertNotIn("tiny_effect", self.model.beliefs)
        finally:
            store.close()

    def _limitation_mapping(self):
        return {"limited_memory_recall": {
            "description": "Investigate and improve long-term memory retrieval",
            "drive": "self_improvement",
        }}

    def test_observed_limitation_produces_goal_with_evidence_provenance(self):
        self.model.update(
            {"limited_memory_recall": "Recall accuracy below target"},
            cycle_id="cycle-20",
            evidence_refs={"limited_memory_recall": "benchmark:recall-20"},
            known_limitations=["limited_memory_recall"],
        )
        result = self.bridge.propose_goals_from_limitations(self._limitation_mapping())
        self.assertEqual(1, len(result["goals"]))
        self.assertIsInstance(result["goals"][0], GoalCandidate)
        self.assertEqual("address_limitation:limited-memory-recall", result["goals"][0].goal_id)
        self.assertFalse(result["goals"][0].requires_external_action)
        self.assertEqual("observed", result["provenance"][0]["source_status"])
        self.assertEqual("benchmark:recall-20", result["provenance"][0]["evidence_ref"])

    def test_inferred_limitation_requires_explicit_opt_in_and_confidence(self):
        self.model.update(
            {"limited_memory_recall": "Possible recall issue"},
            cycle_id="cycle-21",
            evidence_refs={"limited_memory_recall": "audit:recall-21"},
            statuses={"limited_memory_recall": "inferred"},
            confidences={"limited_memory_recall": 0.85},
            known_limitations=["limited_memory_recall"],
        )
        mapping = self._limitation_mapping()
        self.assertEqual([], self.bridge.propose_goals_from_limitations(mapping)["goals"])
        opted_in = self.bridge.propose_goals_from_limitations(mapping, allow_inferred=True)
        self.assertEqual(1, len(opted_in["goals"]))
        self.assertEqual("inferred", opted_in["provenance"][0]["source_status"])
        self.assertEqual([], self.bridge.propose_goals_from_limitations(
            mapping, allow_inferred=True, minimum_confidence=0.9
        )["goals"])

    def test_unknown_stale_and_unregistered_limitations_are_ignored(self):
        self.model.update(
            {"unknown_limit": None, "stale_limit": "Old report"},
            cycle_id="cycle-22",
            statuses={"unknown_limit": "unknown", "stale_limit": "stale"},
            known_limitations=["unknown_limit", "stale_limit"],
        )
        mappings = {
            "unknown_limit": {"description": "Investigate unknown", "drive": "curiosity"},
            "stale_limit": {"description": "Recheck stale", "drive": "verification"},
            "not_registered": {"description": "Invent a limitation", "drive": "curiosity"},
        }
        self.assertEqual([], self.bridge.propose_goals_from_limitations(mappings)["goals"])

    def test_inferred_limitation_without_evidence_is_not_proposed(self):
        self.model.update(
            {"limited_memory_recall": "Possible recall issue"},
            cycle_id="cycle-23",
            statuses={"limited_memory_recall": "inferred"},
            confidences={"limited_memory_recall": 0.95},
            known_limitations=["limited_memory_recall"],
        )
        self.assertEqual([], self.bridge.propose_goals_from_limitations(
            self._limitation_mapping(), allow_inferred=True
        )["goals"])


    def test_limitation_proposal_flows_through_autonomy_with_provenance(self):
        from machina.autonomy import AutonomyController

        self.model.update(
            {"limited_memory_recall": "Recall accuracy below target"},
            cycle_id="cycle-30",
            evidence_refs={"limited_memory_recall": "benchmark:recall-30"},
            known_limitations=["limited_memory_recall"],
        )
        result = self.bridge.select_goal_from_limitations(
            AutonomyController(), self._limitation_mapping()
        )
        self.assertEqual("address_limitation:limited-memory-recall", result["selected_goal_id"])
        self.assertEqual("benchmark:recall-30", result["selected_provenance"]["evidence_ref"])
        self.assertFalse(result["execution_performed"])
        self.assertEqual("cycle-30", self.model.cycle_id)

    def test_empty_evidence_gated_proposals_produce_no_selection(self):
        from machina.autonomy import AutonomyController

        self.model.update(
            {"limited_memory_recall": None},
            cycle_id="cycle-31",
            statuses={"limited_memory_recall": "unknown"},
            known_limitations=["limited_memory_recall"],
        )
        result = self.bridge.select_goal_from_limitations(
            AutonomyController(), self._limitation_mapping()
        )
        self.assertIsNone(result["selected_goal_id"])
        self.assertIsNone(result["selected_provenance"])
        self.assertEqual([], result["proposals"]["goals"])
        self.assertFalse(result["execution_performed"])

    def test_selection_helper_requires_real_autonomy_controller(self):
        with self.assertRaisesRegex(TypeError, "AutonomyController"):
            self.bridge.select_goal_from_limitations(object(), self._limitation_mapping())

if __name__ == "__main__":
    unittest.main()
