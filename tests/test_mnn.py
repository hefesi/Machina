import unittest

from machina.mnn import Connection, MNN, Unit


class MNNCoreTests(unittest.TestCase):
    def make_network(self):
        net = MNN(weight_limit=2.0)
        net.add_unit(Unit("input", activation="identity"))
        net.add_unit(Unit("output", activation="identity"))
        net.add_connection(Connection("edge", "input", "output", weight=0.5))
        return net

    def test_step_uses_previous_state_and_input_clamping(self):
        net = self.make_network()
        result = net.step({"input": 2.0})
        self.assertEqual(result["input"], 2.0)
        self.assertEqual(result["output"], 0.0)
        result = net.step({"input": 2.0})
        self.assertEqual(result["output"], 1.0)
        self.assertEqual(net.timestep, 2)

    def test_hebbian_learning_updates_and_is_bounded(self):
        net = self.make_network()
        net.units["input"].state = 2.0
        net.units["output"].state = 1.0
        changes = net.apply_hebbian(learning_rate=0.5, reward=1.0)
        self.assertEqual(changes["edge"], 1.0)
        self.assertEqual(net.connections["edge"].weight, 1.5)
        net.apply_hebbian(learning_rate=10.0)
        self.assertEqual(net.connections["edge"].weight, 2.0)

    def test_negative_reward_reduces_coactive_weight(self):
        net = self.make_network()
        net.units["input"].state = 1.0
        net.units["output"].state = 1.0
        net.apply_hebbian(learning_rate=0.1, reward=-1.0)
        self.assertAlmostEqual(net.connections["edge"].weight, 0.4)

    def test_snapshot_round_trip_preserves_state_and_topology(self):
        net = self.make_network()
        net.step({"input": 1.0})
        restored = MNN.from_snapshot(net.snapshot())
        self.assertEqual(restored.snapshot(), net.snapshot())

    def test_rejects_missing_endpoints_duplicate_ids_and_nonfinite_values(self):
        net = MNN()
        net.add_unit(Unit("a"))
        with self.assertRaises(ValueError):
            net.add_connection(Connection("bad", "a", "missing"))
        with self.assertRaises(ValueError):
            net.add_unit(Unit("a"))
        with self.assertRaises(ValueError):
            net.step({"a": float("nan")})

    def test_disabled_edges_do_not_transmit_or_learn(self):
        net = self.make_network()
        edge = net.connections["edge"]
        edge.enabled = False
        net.units["input"].state = 1.0
        net.units["output"].state = 1.0
        self.assertEqual(net.step()["output"], 0.0)
        self.assertEqual(net.apply_hebbian(learning_rate=1.0), {})


if __name__ == "__main__":
    unittest.main()
