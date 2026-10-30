import unittest

from machina.self_model import SelfModel
from machina.self_regulation import SelfRegulationController


class SelfRegulationControllerTests(unittest.TestCase):
    def setUp(self):
        self.model = SelfModel()
        self.model.update(
            {
                "internal.mnn.prediction_error": 0.8,
                "internal.mnn.exploration_drive": 0.1,
                "internal.mnn.attention_gain": 0.7,
            },
            cycle_id="cycle-4",
            evidence_refs={
                "internal.mnn.prediction_error": "step:4",
                "internal.mnn.exploration_drive": "step:4",
                "internal.mnn.attention_gain": "step:4",
            },
        )
        self.controller = SelfRegulationController(
            self.model,
            {
                "prediction_error": "error_recovery",
                "exploration_drive": "exploration",
                "attention_gain": "focus",
            },
            targets={
                "prediction_error": 0.0,
                "exploration_drive": 0.5,
                "attention_gain": 0.5,
            },
        )

    def test_proposes_bounded_auditable_adjustments(self):
        proposal = self.controller.propose()
        self.assertEqual("cycle-4", proposal.cycle_id)
        self.assertAlmostEqual(0.12, proposal.adjustments["error_recovery"])
        self.assertEqual(-0.06, proposal.adjustments["exploration"])
        self.assertAlmostEqual(0.03, proposal.adjustments["focus"])
        self.assertEqual(("step:4",), proposal.evidence_refs)
        self.assertEqual(3, len(proposal.rationale))

    def test_missing_or_unknown_telemetry_is_not_guessed(self):
        model = SelfModel()
        model.update(
            {"internal.mnn.prediction_error": None},
            cycle_id="c1",
            statuses={"internal.mnn.prediction_error": "unknown"},
        )
        controller = SelfRegulationController(
            model, {"prediction_error": "recovery"},
            targets={"prediction_error": 0.0},
        )
        proposal = controller.propose()
        self.assertEqual({}, proposal.adjustments)
        self.assertEqual((), proposal.evidence_refs)

    def test_proposal_does_not_mutate_self_model(self):
        before = self.model.snapshot()
        self.controller.propose()
        self.assertEqual(before, self.model.snapshot())

    def test_rejects_unbounded_policy_and_invalid_metrics(self):
        with self.assertRaises(ValueError):
            SelfRegulationController(
                self.model, {"prediction_error": "recovery"},
                targets={"prediction_error": 0.0}, gain=0.5,
            )
        with self.assertRaises(ValueError):
            SelfRegulationController(
                self.model, {"unknown": "recovery"},
                targets={"unknown": 0.0},
            )


if __name__ == "__main__":
    unittest.main()
