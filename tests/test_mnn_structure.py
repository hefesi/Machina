from __future__ import annotations

import unittest

from machina import ActivityGrowthPolicy
from machina.mnn import Connection, MNN, Unit


class ActivityGrowthPolicyTests(unittest.TestCase):
    def make_network(self, *, units=("a", "b", "c", "d")) -> MNN:
        network = MNN(weight_limit=2.0)
        for unit_id in units:
            network.add_unit(Unit(unit_id, activation="identity"))
        return network

    def test_grows_top_coactive_pairs_deterministically(self):
        network = self.make_network()
        network.units["a"].state = 1.0
        network.units["b"].state = 1.0
        network.units["c"].state = 0.5
        network.units["d"].state = 0.1
        policy = ActivityGrowthPolicy(
            max_new_connections=2,
            allowed_targets={"c", "d"},
        )

        grown = policy.grow(network)

        self.assertEqual(
            [(item.connection.source, item.connection.target) for item in grown],
            [("a", "c"), ("b", "c")],
        )
        self.assertEqual([item.score for item in grown], [0.5, 0.5])
        self.assertEqual(grown[0].connection.weight, 0.1)
        self.assertIn(grown[0].connection.id, network.connections)

    def test_skips_existing_pairs_self_edges_and_silent_units(self):
        network = self.make_network(units=("a", "b", "c"))
        network.add_connection(Connection("existing", "a", "b", 0.2))
        network.units["a"].state = 1.0
        network.units["b"].state = 1.0
        network.units["c"].state = 0.0
        policy = ActivityGrowthPolicy(max_new_connections=10, min_activity=0.2)

        grown = policy.grow(network)

        pairs = {(item.connection.source, item.connection.target) for item in grown}
        self.assertNotIn(("a", "b"), pairs)
        self.assertNotIn(("a", "a"), pairs)
        self.assertNotIn(("b", "b"), pairs)
        self.assertFalse(any("c" in pair for pair in pairs))
        self.assertIn(("a", "b"), {(edge.source, edge.target) for edge in network.connections.values()})
        self.assertEqual(grown[0].connection.weight, 0.1)

    def test_respects_connection_and_degree_limits(self):
        network = self.make_network()
        for unit in network.units.values():
            unit.state = 1.0
        policy = ActivityGrowthPolicy(
            max_new_connections=10,
            max_connections=2,
            max_out_degree=1,
            max_in_degree=1,
        )

        grown = policy.grow(network)

        self.assertEqual(len(grown), 2)
        self.assertEqual(len(network.connections), 2)
        out_degrees = [
            sum(1 for edge in network.connections.values() if edge.source == unit_id)
            for unit_id in network.units
        ]
        in_degrees = [
            sum(1 for edge in network.connections.values() if edge.target == unit_id)
            for unit_id in network.units
        ]
        self.assertTrue(all(degree <= 1 for degree in out_degrees))
        self.assertTrue(all(degree <= 1 for degree in in_degrees))

    def test_explicit_activity_and_minimum_threshold(self):
        network = self.make_network(units=("a", "b"))
        network.units["a"].state = 1.0
        network.units["b"].state = 1.0
        policy = ActivityGrowthPolicy(min_activity=2.0)

        self.assertEqual(policy.grow(network), [])
        grown = policy.grow(network, activity={"a": 3.0, "b": -3.0})
        self.assertEqual(len(grown), 1)
        self.assertEqual(grown[0].score, 9.0)

        with self.assertRaisesRegex(ValueError, "unknown units"):
            policy.grow(network, activity={"missing": 1.0})
        with self.assertRaisesRegex(ValueError, "must be finite"):
            policy.grow(network, activity={"a": float("nan")})
        with self.assertRaisesRegex(ValueError, "must be finite"):
            policy.grow(network, activity={"a": True})

    def test_zero_budget_is_a_noop(self):
        network = self.make_network(units=("a", "b"))
        network.units["a"].state = 1.0
        network.units["b"].state = 1.0
        policy = ActivityGrowthPolicy(max_new_connections=0)
        self.assertEqual(policy.grow(network), [])
        self.assertEqual(network.connections, {})

    def test_invalid_configuration_is_rejected(self):
        cases = {
            "negative max new": {"max_new_connections": -1},
            "boolean max new": {"max_new_connections": True},
            "zero weight": {"initial_weight": 0},
            "negative weight": {"initial_weight": -0.1},
            "non-finite weight": {"initial_weight": float("inf")},
            "negative activity": {"min_activity": -0.1},
            "non-finite activity": {"min_activity": float("nan")},
            "negative max connections": {"max_connections": -1},
            "boolean max connections": {"max_connections": True},
            "negative out degree": {"max_out_degree": -1},
            "negative in degree": {"max_in_degree": -1},
            "string source set": {"allowed_sources": "a"},
            "non-iterable source set": {"allowed_sources": 1},
            "empty source id": {"allowed_sources": {""}},
        }
        for label, kwargs in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    ActivityGrowthPolicy(**kwargs)

    def test_grown_topology_survives_snapshot_round_trip(self):
        network = self.make_network(units=("a", "b"))
        network.units["a"].state = 1.0
        network.units["b"].state = 1.0
        grown = ActivityGrowthPolicy().grow(network)
        restored = MNN.from_snapshot(network.snapshot())

        edge = grown[0].connection
        self.assertIn(edge.id, restored.connections)
        self.assertEqual(restored.connections[edge.id].source, "a")
        self.assertEqual(restored.connections[edge.id].target, "b")
        self.assertEqual(restored.connections[edge.id].weight, edge.weight)


if __name__ == "__main__":
    unittest.main()
