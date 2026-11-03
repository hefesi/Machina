import unittest

from machina.curiosity_selector import (
    CuriosityCandidate,
    CuriositySelector,
)


def candidate(candidate_id, question, **overrides):
    values = {
        "candidate_id": candidate_id,
        "gap_property": "memory.coherence",
        "question": question,
        "hypothesis": "A missing relation may explain the inconsistency.",
        "uncertainty": 0.8,
        "expected_information_gain": 0.9,
        "relevance": 0.8,
        "novelty": 0.8,
        "estimated_cost": 0.2,
        "risk": 0.05,
    }
    values.update(overrides)
    return CuriosityCandidate(**values)


class CuriositySelectorTests(unittest.TestCase):
    def setUp(self):
        self.selector = CuriositySelector()

    def test_selects_high_information_relevant_candidate_without_reward(self):
        strong = candidate("strong", "Investigate memory conflict")
        weak = candidate(
            "weak", "Inspect an already understood topic",
            uncertainty=0.2, expected_information_gain=0.1,
            relevance=0.2, novelty=0.1,
        )
        result = self.selector.rank([weak, strong])
        self.assertEqual("strong", result.selected.candidate_id)
        self.assertGreater(result.ranked[0]["score"]["total"], result.ranked[1]["score"]["total"])

    def test_stability_pressure_reduces_exploration_weight(self):
        proposal = candidate("explore", "Explore a novel hypothesis")
        calm = self.selector.rank([proposal], stability_pressure=0.0)
        pressured = self.selector.rank([proposal], stability_pressure=1.0)
        calm_score = calm.ranked[0]["score"]
        pressured_score = pressured.ranked[0]["score"]
        self.assertEqual(1.0, calm_score["exploration_weight"])
        self.assertEqual(0.25, pressured_score["exploration_weight"])
        self.assertLess(pressured_score["total"], calm_score["total"])

    def test_repeated_question_receives_penalty_case_and_whitespace_insensitive(self):
        proposal = candidate("repeat", "  Investigate   Memory Conflict ")
        result = self.selector.rank(
            [proposal],
            prior_questions=[("MEMORY.COHERENCE", "investigate memory conflict")],
        )
        score = result.ranked[0]["score"]
        self.assertEqual(-0.12, score["repetition_penalty"])

    def test_high_risk_candidate_is_rejected(self):
        result = self.selector.rank([
            candidate("risky", "Do a risky experiment", risk=0.9),
        ])
        self.assertIsNone(result.selected)
        self.assertEqual("risk_above_limit", result.rejected[0]["reason"])

    def test_external_action_is_rejected_by_default(self):
        result = self.selector.rank([
            candidate("external", "Change an external system", requires_external_action=True),
        ])
        self.assertIsNone(result.selected)
        self.assertEqual("external_action_not_authorized", result.rejected[0]["reason"])

    def test_score_and_provenance_are_inspectable(self):
        proposal = candidate(
            "inspect", "Inspect a knowledge gap",
            evidence_refs=("observation:17", "memory:4"),
        )
        result = self.selector.rank([proposal])
        payload = result.to_dict()
        self.assertEqual("observation:17", payload["selected"]["evidence_refs"][0])
        self.assertIn("information_gain", payload["ranked"][0]["score"])
        self.assertIn("not evidence", payload["interpretation"])

    def test_deterministic_tie_break_uses_candidate_id(self):
        first = candidate("b", "Question B")
        second = candidate("a", "Question A")
        result = self.selector.rank([first, second])
        self.assertEqual("a", result.selected.candidate_id)

    def test_rejects_duplicate_ids_and_invalid_pressure(self):
        proposal = candidate("same", "Question")
        with self.assertRaises(ValueError):
            self.selector.rank([proposal, proposal])
        with self.assertRaises(ValueError):
            self.selector.rank([proposal], stability_pressure=1.1)

    def test_rejects_invalid_candidate_values(self):
        with self.assertRaises(ValueError):
            candidate("bad", "Question", uncertainty=float("nan"))
        with self.assertRaises(ValueError):
            candidate("bad", "Question", risk=1.2)
        with self.assertRaises(ValueError):
            candidate("bad", "Question", evidence_refs=("valid", ""))


if __name__ == "__main__":
    unittest.main()
