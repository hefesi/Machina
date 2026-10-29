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

    def test_snapshot_rejects_malformed_fields(self):
        valid = self.make_network().snapshot()
        cases = {
            "not a mapping": [],
            "missing weight limit": {key: value for key, value in valid.items() if key != "weight_limit"},
            "boolean weight limit": {**valid, "weight_limit": True},
            "unknown top-level field": {**valid, "extra": 1},
            "fractional timestep": {**valid, "timestep": 1.5},
            "boolean timestep": {**valid, "timestep": True},
            "units not a list": {**valid, "units": "input"},
            "unit is not a mapping": {**valid, "units": ["input"]},
            "unit has unknown field": {
                **valid,
                "units": [{"id": "a", "bias": 0.0, "state": 0.0, "activation": "tanh", "extra": 1}],
                "connections": [],
            },
            "connection enabled is not boolean": {
                **valid,
                "connections": [{
                    "id": "e", "source": "input", "target": "output",
                    "weight": 1.0, "enabled": "yes",
                }],
            },
            "non-finite unit bias": {**valid, "units": [{"id": "a", "bias": float("nan")}]},
        }
        for label, snapshot in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    MNN.from_snapshot(snapshot)

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

    def test_structural_growth_adds_edge_with_bounded_weight(self):
        net = self.make_network()
        edge = net.grow_connection("new-edge", "output", "input", weight=10.0)
        self.assertEqual(edge.weight, net.weight_limit)
        self.assertIn("new-edge", net.connections)
        with self.assertRaises(ValueError):
            net.grow_connection("duplicate-pair", "output", "input")

    def test_structural_pruning_is_bounded_and_deterministic(self):
        net = self.make_network()
        net.add_connection(Connection("weak-b", "input", "output", weight=0.1))
        net.add_connection(Connection("weak-a", "output", "input", weight=-0.1))
        removed = net.prune_connections(min_abs_weight=0.2, max_remove=1)
        self.assertEqual(removed, ["weak-a"])
        self.assertIn("weak-b", net.connections)
        self.assertEqual(net.prune_connections(min_abs_weight=0.2), ["weak-b"])

    def test_unit_removal_requires_explicit_cascade(self):
        net = self.make_network()
        with self.assertRaises(ValueError):
            net.remove_unit("input")
        removed = net.remove_unit("input", cascade=True)
        self.assertEqual(removed.id, "input")
        self.assertNotIn("edge", net.connections)
        self.assertNotIn("input", net.units)

    def test_pruning_rejects_invalid_limits(self):
        net = self.make_network()
        with self.assertRaises(ValueError):
            net.prune_connections(min_abs_weight=-1.0)
        with self.assertRaises(ValueError):
            net.prune_connections(min_abs_weight=1.0, max_remove=-1)


if __name__ == "__main__":
    unittest.main()
