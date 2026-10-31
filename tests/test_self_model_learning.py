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

    def test_strategy_review_requires_two_complete_windows_without_mutation(self):
        result = self.bridge.review_goal_strategy('research', cycle_id='review-1', window_size=2)
        self.assertFalse(result['accepted'])
        self.assertEqual('insufficient_history', result['reason'])
        self.assertFalse(result['self_model_updated'])
        self.assertEqual({}, self.model.beliefs)

    def test_strategy_review_detects_change_and_preserves_revision_history(self):
        for index, outcome in enumerate((0.2, 0.3, 0.8, 0.9), start=1):
            self.learner.observe('research', outcome, evidence=f'evaluator result {index}', observation_id=f'res-{index}')
        first = self.bridge.review_goal_strategy('research', cycle_id='review-1', window_size=2, minimum_change=0.2)
        self.assertTrue(first['accepted'])
        self.assertEqual('improving', first['review']['assessment'])
        self.assertEqual('retain_and_validate', first['review']['recommendation'])
        self.assertFalse(first['causal_claim'])
        repeated = self.bridge.review_goal_strategy('research', cycle_id='review-2', window_size=2, minimum_change=0.2)
        self.assertTrue(repeated['already_applied'])
        self.assertFalse(repeated['self_model_updated'])
        for index, outcome in enumerate((0.1, 0.1), start=5):
            self.learner.observe('research', outcome, evidence=f'evaluator result {index}', observation_id=f'res-{index}')
        second = self.bridge.review_goal_strategy('research', cycle_id='review-3', window_size=2, minimum_change=0.2)
        self.assertEqual('deteriorating', second['review']['assessment'])
        self.assertEqual('review_strategy', second['review']['recommendation'])
        self.assertIsNotNone(second['revision'])
        self.assertTrue(second['revision']['contradicts_previous'])
        self.assertEqual(1, len(self.model.belief_revision_history))
        self.assertEqual('inferred', self.model.beliefs['strategy_review:research']['status'])

    def test_strategy_review_validates_parameters(self):
        with self.assertRaisesRegex(ValueError, 'window_size'):
            self.bridge.review_goal_strategy('research', cycle_id='c', window_size=1)
        with self.assertRaisesRegex(ValueError, 'minimum_change'):
            self.bridge.review_goal_strategy('research', cycle_id='c', minimum_change=float('nan'))
    def test_curiosity_review_detects_support_contradiction_and_requires_opt_in(self):
        from machina.curiosity import CuriosityInvestigationStore
        store = CuriosityInvestigationStore(Path(self.tmp.name) / "review.sqlite3")
        try:
            store.start_investigation(
                "inv-review", gap_property="memory_recall", question="Does indexing improve recall?",
                hypothesis="Indexing improves recall", selection_reason="test", cycle_id="c1", goal_id="g1",
            )
            store.record_evidence("inv-review", evidence_ref="e1", finding="Recall rose in benchmark", cycle_id="c2")
            store.record_evidence("inv-review", evidence_ref="e2", finding="Recall fell in replication", cycle_id="c2")
            assessments = {
                "e1": {"classification": "support", "confidence": 0.9, "rationale": "Benchmark comparison"},
                "e2": {"classification": "contradict", "confidence": 0.8, "rationale": "Independent replication"},
            }
            report = self.bridge.review_curiosity_investigation(
                store, "inv-review", review_id="review-1", cycle_id="c3",
                evidence_assessments=assessments,
            )
            self.assertEqual("mixed", report["assessment"])
            self.assertFalse(report["self_model_updated"])
            self.assertNotIn("memory_recall", self.model.beliefs)
            applied = self.bridge.review_curiosity_investigation(
                store, "inv-review", review_id="review-2", cycle_id="c4",
                evidence_assessments=assessments, apply_to_self_model=True,
            )
            self.assertTrue(applied["self_model_updated"])
            self.assertEqual("inferred", self.model.beliefs["memory_recall"]["status"])
            self.assertEqual("mixed", self.model.beliefs["memory_recall"]["value"]["assessment"])
            repeated = self.bridge.review_curiosity_investigation(
                store, "inv-review", review_id="review-2", cycle_id="c5",
                evidence_assessments=assessments, apply_to_self_model=True,
            )
            self.assertTrue(repeated["already_reviewed"])
            self.assertEqual(0, len(self.model.belief_revision_history))
        finally:
            store.close()

    def test_curiosity_review_rejects_unstored_refs_and_insufficient_evidence(self):
        from machina.curiosity import CuriosityInvestigationStore
        store = CuriosityInvestigationStore(Path(self.tmp.name) / "review-invalid.sqlite3")
        try:
            store.start_investigation(
                "inv", gap_property="capability", question="Can it do X?", hypothesis="It can do X",
                selection_reason="test", cycle_id="c1", goal_id="g1",
            )
            store.record_evidence("inv", evidence_ref="e1", finding="Some result", cycle_id="c2")
            with self.assertRaisesRegex(ValueError, "stored in this investigation"):
                self.bridge.review_curiosity_investigation(
                    store, "inv", review_id="bad", cycle_id="c3",
                    evidence_assessments={"foreign": {"classification": "support", "rationale": "x"}},
                )
            result = self.bridge.review_curiosity_investigation(
                store, "inv", review_id="thin", cycle_id="c3",
                evidence_assessments={"e1": {"classification": "neutral", "rationale": "inconclusive"}},
                apply_to_self_model=True, minimum_assessments=2,
            )
            self.assertEqual("insufficient", result["assessment"])
            self.assertFalse(result["self_model_updated"])
        finally:
            store.close()

    def test_follow_up_curiosity_proposes_only_recorded_unknowns_and_deduplicates(self):
        from machina.curiosity import CuriosityInvestigationStore
        store = CuriosityInvestigationStore(Path(self.tmp.name) / "followups.sqlite3")
        try:
            store.start_investigation(
                "inv-parent", gap_property="memory_recall", question="Does indexing improve recall?",
                hypothesis="Indexing improves recall", selection_reason="test", cycle_id="c1", goal_id="g1",
            )
            store.close_investigation(
                "inv-parent", outcome="partially_answered", answer_summary="Some evidence gathered",
                remaining_unknowns=["Does recall remain stable after restart?", "What is the memory cost?"],
                cycle_id="c2",
            )
            mappings = {
                "Does recall remain stable after restart?": {"information_gain": 0.9, "impact": 0.8},
                "What is the memory cost?": {"question": "Measure memory cost under load", "risk": 0.01},
            }
            result = self.bridge.propose_follow_up_curiosity_goals(store, "inv-parent", mappings)
            self.assertEqual(2, len(result["goals"]))
            self.assertTrue(all(not goal.requires_external_action for goal in result["goals"]))
            self.assertEqual("Does recall remain stable after restart?", result["goals"][0].description)
            self.assertEqual("inv-parent", result["provenance"][0]["source_investigation_id"])
            store.start_investigation(
                "inv-child", gap_property="memory_recall",
                question="Does recall remain stable after restart?", hypothesis="Recall remains stable",
                selection_reason="follow-up", cycle_id="c3", goal_id="g2",
            )
            deduped = self.bridge.propose_follow_up_curiosity_goals(store, "inv-parent", mappings)
            self.assertEqual(1, len(deduped["goals"]))
            self.assertEqual("prior_investigation_exists", deduped["suppressed"][0]["reason"])
        finally:
            store.close()

    def test_follow_up_curiosity_requires_closed_investigation_and_known_unknowns(self):
        from machina.curiosity import CuriosityInvestigationStore
        store = CuriosityInvestigationStore(Path(self.tmp.name) / "followups-invalid.sqlite3")
        try:
            store.start_investigation(
                "inv-open", gap_property="capability", question="Can it do X?", hypothesis="It can do X",
                selection_reason="test", cycle_id="c1", goal_id="g1",
            )
            with self.assertRaisesRegex(ValueError, "closed investigation"):
                self.bridge.propose_follow_up_curiosity_goals(store, "inv-open", {})
            store.close_investigation(
                "inv-open", outcome="unanswered", answer_summary="No conclusive answer",
                remaining_unknowns=["What evidence would resolve this?"], cycle_id="c2",
            )
            with self.assertRaisesRegex(ValueError, "remaining_unknowns"):
                self.bridge.propose_follow_up_curiosity_goals(
                    store, "inv-open", {"Invented question": {"information_gain": 0.8}}
                )
        finally:
            store.close()

    def test_curiosity_proposes_only_unknown_stale_and_low_confidence_gaps(self):
        self.model.update(
            {"known": "settled", "uncertain": "tentative", "outdated": "old"},
            cycle_id="c1",
            evidence_refs={"known": "e-known", "uncertain": "e-uncertain", "outdated": "e-old"},
            statuses={"known": "observed", "uncertain": "inferred", "outdated": "stale"},
            confidences={"uncertain": 0.3, "outdated": 0.2},
        )
        mappings = {
            "missing": {"question": "What evidence supports this capability?", "information_gain": 0.9, "impact": 0.8},
            "uncertain": {"question": "Can this estimate be reproduced?", "information_gain": 0.7, "impact": 0.6},
            "outdated": {"question": "Is the old estimate still valid?", "information_gain": 0.5, "impact": 0.7},
            "known": {"question": "Recheck settled evidence"},
        }
        result = self.bridge.propose_curiosity_goals(mappings)
        self.assertEqual({"investigate_gap:missing", "investigate_gap:uncertain", "investigate_gap:outdated"},
                         {goal.goal_id for goal in result["goals"]})
        self.assertTrue(all(not goal.requires_external_action for goal in result["goals"]))
        self.assertFalse(result["execution_performed"])
        by_property = {item["belief_property"]: item for item in result["provenance"]}
        self.assertEqual("e-uncertain", by_property["uncertain"]["belief_evidence_ref"])

    def test_curiosity_selection_uses_bounded_autonomy_without_execution(self):
        from machina.autonomy import AutonomyController
        result = self.bridge.select_curiosity_goal(
            AutonomyController(),
            {
                "memory_gap": {"question": "Which memory source is missing?", "information_gain": 0.9, "impact": 0.9, "risk": 0.01},
                "model_gap": {"question": "Which model assumption needs testing?", "information_gain": 0.5, "impact": 0.4, "risk": 0.02},
            },
        )
        self.assertIsNotNone(result["selected_goal_id"])
        self.assertFalse(result["execution_performed"])
        self.assertFalse(result["selected_provenance"]["execution_performed"])

    def test_curiosity_rejects_invalid_information_value_and_external_action_flag(self):
        with self.assertRaisesRegex(ValueError, "information_gain"):
            self.bridge.propose_curiosity_goals({"gap": {"question": "Investigate", "information_gain": 2}})
        result = self.bridge.propose_curiosity_goals({"gap": {"question": "Investigate", "requires_external_action": True}})
        self.assertFalse(result["goals"][0].requires_external_action)
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
                store.record_trial("exp-1", "treatment", treatment, evidence_ref=f"et-{index}{suffix}", trial_id=f"t-{index}{suffix}", context_key=context)
                store.record_trial("exp-1", "control", control, evidence_ref=f"ec-{index}{suffix}", trial_id=f"c-{index}{suffix}", context_key=context)
            else:
                store.record_trial("exp-1", "treatment", treatment, evidence_ref=f"et-{index}{suffix}", trial_id=f"t-{index}{suffix}")
                store.record_trial("exp-1", "control", control, evidence_ref=f"ec-{index}{suffix}", trial_id=f"c-{index}{suffix}")
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
