import unittest

from machina.self_autobiographical_evaluation import (
    SelfAutobiographicalEvaluation, SelfExperienceAssessment,
)
from machina.mnn_autobiographical_learning import MNNAutobiographicalLearningAdvisor


class MNNAutobiographicalLearningAdvisorTests(unittest.TestCase):
    def assessment(self, count, outcome, error):
        return SelfExperienceAssessment(
            transformation_event_id="transform:1",
            changed_paths=("capability.reasoning",),
            experience_count=count,
            successful_count=0, unsuccessful_count=0, neutral_count=count,
            mean_outcome=outcome,
            mean_absolute_prediction_error=error,
            evidence_refs=("evidence:1",),
            interpretation="Association is not causation.",
        )

    def evaluate(self, item):
        return SelfAutobiographicalEvaluation(
            assessments=(item,), aggregate_experience_count=item.experience_count,
            limitations=("Descriptive only.",),
        )

    def test_insufficient_sample_does_not_recommend_update(self):
        signals = MNNAutobiographicalLearningAdvisor().advise(
            self.evaluate(self.assessment(2, 0.95, 0.01))
        )
        self.assertEqual("insufficient_evidence", signals[0].recommendation)

    def test_positive_outcome_and_calibration_become_reinforcement_candidate(self):
        signals = MNNAutobiographicalLearningAdvisor().advise(
            self.evaluate(self.assessment(5, 0.85, 0.1))
        )
        self.assertEqual("candidate_for_reinforcement", signals[0].recommendation)
        self.assertEqual(("evidence:1",), signals[0].evidence_refs)

    def test_positive_outcome_without_calibration_only_requests_monitoring(self):
        signals = MNNAutobiographicalLearningAdvisor().advise(
            self.evaluate(self.assessment(5, 0.9, None))
        )
        self.assertEqual("monitor_calibration", signals[0].recommendation)

    def test_negative_outcome_requests_review_not_automatic_reversal(self):
        signals = MNNAutobiographicalLearningAdvisor().advise(
            self.evaluate(self.assessment(5, 0.1, 0.05))
        )
        self.assertEqual("review_or_revise", signals[0].recommendation)

    def test_intermediate_outcome_requests_more_observation(self):
        signals = MNNAutobiographicalLearningAdvisor().advise(
            self.evaluate(self.assessment(5, 0.5, 0.1))
        )
        self.assertEqual("continue_observation", signals[0].recommendation)

    def test_invalid_thresholds_are_rejected(self):
        with self.assertRaises(ValueError):
            MNNAutobiographicalLearningAdvisor(minimum_observations=0)
        with self.assertRaises(ValueError):
            MNNAutobiographicalLearningAdvisor(
                negative_outcome_threshold=0.8,
                positive_outcome_threshold=0.2,
            )


if __name__ == "__main__":
    unittest.main()
