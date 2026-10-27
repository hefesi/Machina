import json
import unittest

from machina.mnn import Connection, MNN, Unit
from machina.mnn_experience import MNNExperienceCycle


class MNNExperienceCycleTests(unittest.TestCase):
    def make_cycle(self):
        network = MNN(weight_limit=2.0)
        network.add_unit(Unit("action", activation="identity"))
        network.add_unit(Unit("outcome", activation="identity"))
        network.add_connection(Connection("action-outcome", "action", "outcome", 0.5))
        return MNNExperienceCycle(network, learning_rate=0.1)

    def test_delayed_outcome_updates_prior_eligible_connection(self):
        cycle = self.make_cycle()
        initial = cycle.network.connections["action-outcome"].weight
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})
        result = cycle.resolve(1.0)
        self.assertGreater(cycle.network.connections["action-outcome"].weight, initial)
        self.assertEqual(result["pending_steps"], 2)
        self.assertEqual(cycle.pending_steps, 0)
        self.assertEqual(cycle.modulator.eligibility, {})

    def test_neutral_steps_do_not_change_weights(self):
        cycle = self.make_cycle()
        initial = cycle.network.connections["action-outcome"].weight
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})
        self.assertEqual(cycle.network.connections["action-outcome"].weight, initial)

    def test_snapshot_restores_in_flight_experience(self):
        cycle = self.make_cycle()
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})
        restored = MNNExperienceCycle.from_snapshot(json.loads(json.dumps(cycle.snapshot())))
        self.assertEqual(restored.pending_steps, 2)
        self.assertEqual(restored.snapshot(), cycle.snapshot())
        result = restored.resolve(1.0)
        self.assertGreater(result["weight_changes"]["action-outcome"], 0.0)

    def test_cannot_resolve_without_pending_experience(self):
        with self.assertRaises(RuntimeError):
            self.make_cycle().resolve(1.0)

    def test_invalid_snapshot_rejects_unknown_eligibility_edge(self):
        data = self.make_cycle().snapshot()
        data["modulator"]["eligibility"] = {"missing-edge": 0.5}
        data["pending_steps"] = 1
        with self.assertRaisesRegex(ValueError, "unknown edges"):
            MNNExperienceCycle.from_snapshot(data)

    def test_learning_rate_must_be_finite_and_nonnegative(self):
        with self.assertRaises(ValueError):
            MNNExperienceCycle(self.make_cycle().network, learning_rate=-1)
        with self.assertRaises(ValueError):
            MNNExperienceCycle(self.make_cycle().network, learning_rate=float("nan"))


if __name__ == "__main__":
    unittest.main()
