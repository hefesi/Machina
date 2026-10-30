from __future__ import annotations

import json
import unittest

from machina.chemical_signaling import ChemicalEvent
from machina.mnn import Connection, MNN, Unit
from machina.mnn_organism import MNNOrganism
from machina.self_continuity import SelfContinuity


class MNNOrganismTests(unittest.TestCase):
    def make_organism(self):
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        network.add_unit(Unit("dopamine", activation="identity"))
        network.add_unit(Unit("integrator", activation="tanh"))
        network.add_connection(Connection("sensor-integrator", "sensor", "integrator", 0.4))
        network.add_connection(Connection("dopamine-integrator", "dopamine", "integrator", 0.2))
        return MNNOrganism(
            "machina-test",
            network,
            chemical_inputs={"dopamine": "dopamine"},
            learning_rate=0.01,
        )

    def test_one_tick_advances_all_subsystems_together(self):
        organism = self.make_organism()
        result = organism.step(
            {"sensor": 0.7},
            ChemicalEvent(reward=0.8, novelty=0.6, progress=0.4),
        )
        self.assertEqual(result.timestep, 1)
        self.assertEqual(organism.network.timestep, 1)
        self.assertEqual(organism.signaling.state.timestep, 1)
        self.assertEqual(len(organism.continuity.event_history), 1)
        self.assertIn("dopamine", result.neural_state)

    def test_chemical_modulation_reaches_configured_neural_unit(self):
        organism = self.make_organism()
        result = organism.step(event=ChemicalEvent(reward=1.0))
        self.assertAlmostEqual(
            organism.network.units["dopamine"].state,
            result.chemical_state["dopamine"],
        )

    def test_snapshot_round_trip_preserves_coupled_state(self):
        organism = self.make_organism()
        organism.step({"sensor": 0.5}, ChemicalEvent(reward=0.9, novelty=0.3))
        snapshot = json.loads(json.dumps(organism.snapshot()))
        restored = MNNOrganism.from_snapshot(snapshot)
        self.assertEqual(restored.snapshot(), snapshot)
        next_a = organism.step({"sensor": 0.2}, ChemicalEvent(reward=0.1))
        next_b = restored.step({"sensor": 0.2}, ChemicalEvent(reward=0.1))
        self.assertEqual(next_a, next_b)
        self.assertEqual(organism.snapshot(), restored.snapshot())

    def test_invalid_input_does_not_advance_any_subsystem(self):
        organism = self.make_organism()
        before = organism.snapshot()
        with self.assertRaises(ValueError):
            organism.step({"missing": 1.0})
        self.assertEqual(organism.snapshot(), before)

    def test_rejects_mismatched_identity_or_clocks(self):
        with self.assertRaises(ValueError):
            MNNOrganism("a", continuity=SelfContinuity("b"))
        network = MNN()
        network.timestep = 1
        with self.assertRaises(ValueError):
            MNNOrganism("a", network=network)

    def test_chemical_routes_must_reference_real_units(self):
        with self.assertRaises(ValueError):
            MNNOrganism("a", chemical_inputs={"dopamine": "missing"})


if __name__ == "__main__":
    unittest.main()
