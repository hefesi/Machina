import unittest

from machina.curiosity_policy import CuriosityQuestion, CuriositySelector


class CuriositySelectorTests(unittest.TestCase):
    def setUp(self):
        self.selector = CuriositySelector()

    def question(self, name="q1", **overrides):
        values = dict(
            question_id=name, gap_property="causal_model",
            question="Which factor explains the observed change?",
            hypothesis="A context variable moderates the effect",
            uncertainty=0.9, expected_information_gain=0.9,
            relevance=0.8, novelty=0.8, estimated_cost=0.2, risk=0.05,
        )
        values.update(overrides)
        return CuriosityQuestion(**values)

    def test_information_gain_can_drive_selection_without_external_reward(self):
        result = self.selector.choose([self.question()])
        self.assertEqual("q1", result.selected.question_id)
        self.assertGreater(result.ranked[0]["score"]["uncertainty_information_gain"], 0)

    def test_stability_pressure_reduces_exploration(self):
        explore = self.selector.choose([self.question()], stability_pressure=0)
        stable = self.selector.choose([self.question()], stability_pressure=1)
        self.assertGreater(explore.exploration_weight, stable.exploration_weight)
        self.assertLess(
            stable.ranked[0]["score"]["uncertainty_information_gain"],
            explore.ranked[0]["score"]["uncertainty_information_gain"],
        )

    def test_risk_and_external_action_are_rejected_by_default(self):
        result = self.selector.choose([
            self.question("risky", risk=0.9),
            self.question("external", requires_external_action=True),
        ])
        self.assertIsNone(result.selected)
        self.assertEqual(
            {"risk_above_limit", "external_action_not_authorized"},
            {item["reason"] for item in result.rejected},
        )

    def test_repetition_penalty_changes_tie_break(self):
        result = self.selector.choose(
            [self.question("a"), self.question("b")], recent_question_ids=["a"]
        )
        self.assertEqual("b", result.selected.question_id)

    def test_invalid_values_and_duplicate_ids_are_rejected(self):
        with self.assertRaises(ValueError):
            self.question(uncertainty=1.5)
        q = self.question()
        with self.assertRaisesRegex(ValueError, "unique"):
            self.selector.choose([q, q])


if __name__ == "__main__":
    unittest.main()
