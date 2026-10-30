import tempfile
import unittest
from pathlib import Path

from machina.goal_outcome_learning import GoalOutcomeLearner


class GoalOutcomeLearningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "outcomes.sqlite3"
        self.learner = GoalOutcomeLearner(self.path)

    def tearDown(self):
        self.learner.close()
        self.tmp.cleanup()

    def test_prediction_updates_from_observed_outcomes(self):
        before = self.learner.predict("research")
        self.assertEqual(.5, before["predicted_outcome"])
        first = self.learner.observe(
            "research", 1.0, evidence="Evaluator verified the research milestone."
        )
        self.assertEqual(.5, first["prediction_before"])
        self.assertEqual(.5, first["prediction_error"])
        after = self.learner.predict("research")
        self.assertGreater(after["predicted_outcome"], before["predicted_outcome"])
        self.assertEqual(1, after["observations"])

    def test_estimates_can_be_passed_to_goal_scheduler(self):
        self.learner.observe("research", 1.0, evidence="Research delivered.")
        estimates = self.learner.utility_estimates(["research", "deployment"])
        self.assertGreater(estimates["research"], estimates["deployment"])
        self.assertEqual({"research", "deployment"}, set(estimates))

    def test_prediction_is_specific_to_goal_type(self):
        self.learner.observe("research", 1.0, evidence="Research succeeded.")
        self.assertGreater(
            self.learner.predict("research")["predicted_outcome"],
            self.learner.predict("deployment")["predicted_outcome"],
        )

    def test_history_and_learning_survive_restart(self):
        self.learner.observe(
            "documentation", .25, evidence="Only one of four checks passed.",
            observation_id="evaluation-001",
        )
        self.learner.close()
        self.learner = GoalOutcomeLearner(self.path)
        history = self.learner.history("documentation")
        self.assertEqual("evaluation-001", history[0]["observation_id"])
        self.assertEqual(.25, history[0]["outcome"])
        self.assertEqual(1, self.learner.predict("documentation")["observations"])

    def test_duplicate_observation_id_is_rejected(self):
        args = dict(evidence="Verified result.", observation_id="same-event")
        self.learner.observe("build", .8, **args)
        with self.assertRaises(ValueError):
            self.learner.observe("build", .2, **args)
        self.assertEqual(1, self.learner.predict("build")["observations"])

    def test_invalid_outcomes_and_evidence_are_rejected(self):
        with self.assertRaises(ValueError):
            self.learner.observe("build", 1.2, evidence="Invalid range.")
        with self.assertRaises(ValueError):
            self.learner.observe("build", .5, evidence=" ")
        with self.assertRaises(ValueError):
            self.learner.predict(" ")

if __name__ == "__main__":
    unittest.main()
