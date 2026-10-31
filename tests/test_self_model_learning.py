import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
