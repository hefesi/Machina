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
