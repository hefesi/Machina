import unittest

from machina.homeostasis import HomeostaticProposal, HomeostaticRule
from machina.homeostatic_learning import HomeostaticFeedbackLearner


class HomeostaticFeedbackLearnerTests(unittest.TestCase):
    def setUp(self):
        self.rules = {
            "prediction_error": HomeostaticRule(
                "internal.mnn.prediction_error", "error_recovery",
                0.1, 0.4, -0.05, 0.12,
            )
        }
        self.learner = HomeostaticFeedbackLearner(self.rules)
        self.proposal = HomeostaticProposal(
            "cycle-3", {"error_recovery": 0.12},
            {"prediction_error": 0.3}, {"prediction_error": 3},
            ("telemetry:3",), ("persistent deviation",),
        )

    def test_prior_feedback_is_neutral_and_evaluated_success_scales_gain(self):
        initial = self.learner.estimate("prediction_error", "above")
        self.assertEqual(1.0, initial.recommended_gain_scale)
        learned = self.learner.observe(
            "prediction_error", "above", improved=True,
            evidence_ref="evaluation:1", observation_id="outcome-1",
        )
        self.assertGreater(learned.recommended_gain_scale, 1.0)
        adapted = self.learner.adapt(self.proposal)
        self.assertGreater(adapted.adjustments["error_recovery"], 0.12)

    def test_failed_evaluation_reduces_recommended_gain(self):
        estimate = self.learner.observe(
            "prediction_error", "above", improved=False,
            evidence_ref="evaluation:2", observation_id="outcome-2",
        )
        self.assertLess(estimate.recommended_gain_scale, 1.0)

    def test_feedback_is_idempotent_and_conflicts_are_rejected(self):
        args = dict(rule_name="prediction_error", direction="above", improved=True,
                    evidence_ref="evaluation:3", observation_id="same-id")
        first = self.learner.observe(**args)
        second = self.learner.observe(**args)
        self.assertEqual(first, second)
        with self.assertRaises(ValueError):
            self.learner.observe(**{**args, "improved": False})

    def test_requires_explicit_evidence_and_valid_direction(self):
        with self.assertRaises(ValueError):
            self.learner.observe("prediction_error", "sideways", improved=True,
                                 evidence_ref="ev", observation_id="id")
        with self.assertRaises(ValueError):
            self.learner.observe("prediction_error", "above", improved=True,
                                 evidence_ref="", observation_id="id")

    def test_snapshot_round_trip_preserves_posterior(self):
        self.learner.observe("prediction_error", "above", improved=True,
                             evidence_ref="ev:1", observation_id="id:1")
        restored = HomeostaticFeedbackLearner.from_snapshot(self.learner.snapshot())
        self.assertEqual(
            self.learner.estimate("prediction_error", "above"),
            restored.estimate("prediction_error", "above"),
        )

    def test_adaptation_is_bounded_and_does_not_mutate_input(self):
        for index in range(20):
            self.learner.observe("prediction_error", "above", improved=True,
                                 evidence_ref=f"ev:{index}", observation_id=f"id:{index}")
        before = dict(self.proposal.adjustments)
        adapted = self.learner.adapt(self.proposal)
        self.assertLessEqual(abs(adapted.adjustments["error_recovery"]), 0.3)
        self.assertEqual(before, dict(self.proposal.adjustments))


if __name__ == "__main__":
    unittest.main()
