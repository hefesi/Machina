"""Tests for delayed reward assignment through eligibility traces."""
from __future__ import annotations

import unittest

from machina.mnn import Connection, MNN, Unit
from machina.mnn_learning import EligibilityTraceLearner


class EligibilityTraceLearnerTests(unittest.TestCase):
    def make_network(self) -> MNN:
        network = MNN(weight_limit=2.0)
        network.add_unit(Unit("pre", activation="identity"))
        network.add_unit(Unit("post", activation="identity"))
        network.add_connection(Connection("edge", "pre", "post", weight=0.25))
        network.units["pre"].state = 1.0
        network.units["post"].state = 0.5
        return network

    def test_delayed_reward_changes_weight_using_prior_activity(self) -> None:
        network = self.make_network()
        learner = EligibilityTraceLearner(network, learning_rate=0.2, trace_decay=0.5)
        learner.record_activity()
        network.reset_states()
        learner.apply_reward(1.0)
        self.assertAlmostEqual(0.35, network.connections["edge"].weight)

    def test_trace_accumulates_and_is_bounded(self) -> None:
        network = self.make_network()
        learner = EligibilityTraceLearner(network, trace_decay=1.0, trace_limit=0.75)
        learner.record_activity()
        learner.record_activity()
        self.assertAlmostEqual(0.75, learner.traces["edge"])

    def test_negative_reward_reverses_update_direction(self) -> None:
        network = self.make_network()
        learner = EligibilityTraceLearner(network, learning_rate=0.2)
        learner.record_activity()
        learner.apply_reward(-1.0)
        self.assertAlmostEqual(0.15, network.connections["edge"].weight)

    def test_clear_reward_resets_trace_but_not_weight_bounds(self) -> None:
        network = self.make_network()
        learner = EligibilityTraceLearner(network, learning_rate=10.0)
        learner.record_activity()
        learner.apply_reward(1.0, clear=True)
        self.assertEqual(2.0, network.connections["edge"].weight)
        self.assertEqual(0.0, learner.traces["edge"])

    def test_snapshot_round_trip_and_topology_validation(self) -> None:
        network = self.make_network()
        learner = EligibilityTraceLearner(network)
        learner.record_activity()
        saved = learner.snapshot()
        restored = EligibilityTraceLearner(network)
        restored.restore(saved)
        self.assertEqual(saved, restored.snapshot())
        network.grow_connection("new-edge", "post", "pre")
        with self.assertRaises(ValueError):
            restored.restore(saved)

    def test_disabled_edges_do_not_accumulate_or_learn(self) -> None:
        network = self.make_network()
        network.connections["edge"].enabled = False
        learner = EligibilityTraceLearner(network)
        learner.record_activity()
        self.assertEqual(0.0, learner.traces["edge"])
        self.assertEqual({"edge": 0.0}, learner.apply_reward(1.0))

    def test_invalid_parameters_and_rewards_are_rejected(self) -> None:
        network = self.make_network()
        with self.assertRaises(ValueError):
            EligibilityTraceLearner(network, trace_decay=1.1)
        with self.assertRaises(ValueError):
            EligibilityTraceLearner(network, learning_rate=-0.1)
        learner = EligibilityTraceLearner(network)
        with self.assertRaises(ValueError):
            learner.apply_reward(float("nan"))


if __name__ == "__main__":
    unittest.main()
