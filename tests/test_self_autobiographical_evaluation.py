import unittest

from machina.self_autobiographical_recall import SelfAutobiographicalMatch
from machina.self_autobiographical_evaluation import SelfAutobiographicalEvaluator


class SelfAutobiographicalEvaluatorTests(unittest.TestCase):
    def match(self, experiences):
        return SelfAutobiographicalMatch(
            transformation_event_id="event:transform",
            cycle_id="cycle:2",
            sequence=2,
            score=0.8,
            matched_terms=("reasoning",),
            changed_paths=("capability_estimates.reasoning",),
            durability={},
            experience_records=tuple(experiences),
            evidence_refs=("transform:evidence",),
        )

    def experience(self, event_id, actual, expected, prediction_error):
        return {
            "event_id": event_id,
            "content": {
                "actual_outcome": actual,
                "expected_outcome": expected,
                "prediction_error": prediction_error,
            },
        }

    def test_counts_outcomes_and_prediction_error_without_causal_claim(self):
        match = self.match([
            self.experience("e1", 0.9, 0.8, 0.1),
            self.experience("e2", 0.1, 0.7, -0.6),
            self.experience("e3", 0.5, 0.5, 0.0),
        ])
        result = SelfAutobiographicalEvaluator().evaluate([match])
        assessment = result.assessments[0]
        self.assertEqual((1, 1, 1), (
            assessment.successful_count,
            assessment.unsuccessful_count,
            assessment.neutral_count,
        ))
        self.assertAlmostEqual(0.5, assessment.mean_outcome)
        self.assertAlmostEqual((0.1 + 0.6 + 0.0) / 3, assessment.mean_absolute_prediction_error)
        self.assertIn("do not establish", assessment.interpretation)

    def test_missing_outcomes_are_not_guessed(self):
        result = SelfAutobiographicalEvaluator().evaluate([
            self.match([{"event_id": "e1", "content": {"context": "task"}}])
        ])
        self.assertEqual(0, result.aggregate_experience_count)
        self.assertIsNone(result.assessments[0].mean_outcome)

    def test_rejects_out_of_range_and_non_finite_outcomes(self):
        evaluator = SelfAutobiographicalEvaluator()
        with self.assertRaises(ValueError):
            evaluator.evaluate([self.match([self.experience("e1", 1.5, 0.5, 1.0)])])
        with self.assertRaises(ValueError):
            evaluator.evaluate([self.match([self.experience("e1", float("nan"), 0.5, 1.0)])])

    def test_empty_input_is_valid(self):
        result = SelfAutobiographicalEvaluator().evaluate([])
        self.assertEqual((), result.assessments)
        self.assertEqual(0, result.aggregate_experience_count)


if __name__ == "__main__":
    unittest.main()
