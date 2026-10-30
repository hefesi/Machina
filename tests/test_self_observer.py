import unittest

from machina.mnn_organism import OrganismStep
from machina.self_model import SelfModel
from machina.self_observer import MNNStateSelfObserver


class MNNStateSelfObserverTests(unittest.TestCase):
    def setUp(self):
        self.model = SelfModel()
        self.observer = MNNStateSelfObserver(self.model)

    def step(self):
        return OrganismStep(
            timestep=3,
            neural_state={"reasoning": 0.7, "memory": -0.2},
            chemical_state={"dopamine": 0.4},
            prediction_error=-0.1,
            exploration_drive=0.6,
            plasticity_gain=0.8,
            attention_gain=0.9,
            weight_changes={"edge-1": 0.01},
            motivation_urgencies={"curiosity": 0.75},
        )

    def test_records_neural_and_internal_telemetry_with_provenance(self):
        result = self.observer.observe(
            self.step(), cycle_id="cycle-3", evidence_ref="organism-step:3"
        )
        beliefs = result["beliefs"]
        activation = beliefs["internal.mnn.activation.reasoning"]
        self.assertEqual(0.7, activation["value"])
        self.assertEqual("observed", activation["status"])
        self.assertEqual("organism-step:3", activation["evidence_ref"])
        self.assertEqual(0.75, beliefs["internal.mnn.motivation.curiosity"]["value"])
        self.assertEqual("cycle-3", result["cycle_id"])

    def test_does_not_claim_capability_or_emotion(self):
        self.observer.observe(self.step(), cycle_id="c3", evidence_ref="step:3")
        self.assertEqual({}, self.model.capability_estimates)
        self.assertNotIn("internal.emotion", self.model.beliefs)

    def test_invalid_telemetry_is_rejected_without_partial_update(self):
        step = self.step()
        bad = OrganismStep(
            timestep=step.timestep, neural_state={"reasoning": float("nan")},
            chemical_state=step.chemical_state, prediction_error=step.prediction_error,
            exploration_drive=step.exploration_drive, plasticity_gain=step.plasticity_gain,
            attention_gain=step.attention_gain, weight_changes=step.weight_changes,
            motivation_urgencies=step.motivation_urgencies,
        )
        with self.assertRaises(ValueError):
            self.observer.observe(bad, cycle_id="c3", evidence_ref="step:3")
        self.assertEqual({}, self.model.beliefs)

    def test_requires_explicit_evidence_and_completed_step(self):
        with self.assertRaises(ValueError):
            self.observer.observe(self.step(), cycle_id="c3", evidence_ref="")
        with self.assertRaises(TypeError):
            self.observer.observe({}, cycle_id="c3", evidence_ref="step:3")


if __name__ == "__main__":
    unittest.main()
