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


if __name__ == "__main__":
    unittest.main()
