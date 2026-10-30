import unittest

from machina.mnn import Connection, MNN, Unit
from machina.mnn_short_term_plasticity import MNNShortTermPlasticity


class MNNShortTermPlasticityTests(unittest.TestCase):
    def make_network(self):
        network = MNN()
        network.add_unit(Unit("pre", activation="identity", state=0.0))
        network.add_unit(Unit("post", activation="identity", state=0.0))
        network.add_connection(Connection("edge", "pre", "post", 1.0))
        return network

    def test_transient_dynamics_change_transmission_not_long_term_weight(self):
        network = self.make_network()
        dynamics = MNNShortTermPlasticity(
            network, baseline_utilization=0.2, facilitation_rate=0.5, recovery_rate=0.0
        )
        network.units["pre"].state = 1.0
        original_weight = network.connections["edge"].weight
        gains = dynamics.gains(network)
        self.assertGreater(gains["edge"], 0.0)
        self.assertLess(network.connections["edge"].weight, original_weight + 1e-12)
        self.assertEqual(original_weight, network.connections["edge"].weight)

    def test_inactive_source_allows_resource_recovery(self):
        network = self.make_network()
        dynamics = MNNShortTermPlasticity(network, recovery_rate=0.5)
        network.units["pre"].state = 1.0
        dynamics.gains(network)
        depleted = dynamics.resources["edge"]
        network.units["pre"].state = 0.0
        dynamics.gains(network)
        self.assertGreater(dynamics.resources["edge"], depleted)

    def test_step_routes_gains_into_network(self):
        network = self.make_network()
        dynamics = MNNShortTermPlasticity(network)
        network.units["pre"].state = 1.0
        state = dynamics.step(network)
        self.assertEqual(1, network.timestep)
        self.assertIn("post", state)

    def test_snapshot_round_trip(self):
        network = self.make_network()
        dynamics = MNNShortTermPlasticity(network)
        network.units["pre"].state = 1.0
        dynamics.gains(network)
        restored = MNNShortTermPlasticity.from_snapshot(dynamics.snapshot(), network)
        self.assertEqual(dynamics.snapshot(), restored.snapshot())

    def test_snapshot_rejects_different_topology(self):
        network = self.make_network()
        dynamics = MNNShortTermPlasticity(network)
        other = MNN()
        other.add_unit(Unit("pre"))
        other.add_unit(Unit("post"))
        other.add_connection(Connection("different", "pre", "post"))
        with self.assertRaises(ValueError):
            MNNShortTermPlasticity.from_snapshot(dynamics.snapshot(), other)

    def test_invalid_gains_and_topology_drift_are_rejected(self):
        network = self.make_network()
        with self.assertRaises(ValueError):
            network.step(connection_gains={"missing": 1.0})
        dynamics = MNNShortTermPlasticity(network)
        network.add_unit(Unit("other"))
        network.add_connection(Connection("new", "pre", "other"))
        with self.assertRaises(ValueError):
            dynamics.gains(network)


if __name__ == "__main__":
    unittest.main()
