import unittest

from machina.mnn import Connection, MNN, Unit
from machina.mnn_reward import RewardModulator


class RewardModulatorTests(unittest.TestCase):
    def make_network(self):
        net = MNN(weight_limit=2.0)
        net.add_unit(Unit("pre", activation="identity", state=1.0))
        net.add_unit(Unit("post", activation="identity", state=1.0))
        net.add_connection(Connection("edge", "pre", "post", weight=0.5))
        return net

    def test_first_reward_reinforces_eligible_connection(self):
        net = self.make_network()
        modulator = RewardModulator()
        changes = modulator.update(net, reward=1.0, learning_rate=0.1)
        self.assertAlmostEqual(changes["edge"], 0.1)
        self.assertAlmostEqual(net.connections["edge"].weight, 0.6)

    def test_delayed_reward_uses_eligibility_trace(self):
        net = self.make_network()
        modulator = RewardModulator(trace_decay=0.5, baseline_rate=0.5)
        modulator.update(net, reward=0.0, learning_rate=0.1)
        net.units["pre"].state = 1.0
        net.units["post"].state = 0.0
        modulator.update(net, reward=0.0, learning_rate=0.1)
        self.assertAlmostEqual(modulator.eligibility["edge"], 0.5)
        net.units["post"].state = 1.0
        changes = modulator.update(net, reward=1.0, learning_rate=0.1)
        self.assertGreater(changes["edge"], 0.0)

    def test_negative_prediction_error_reduces_weight(self):
        net = self.make_network()
        modulator = RewardModulator(baseline_rate=1.0)
        modulator.update(net, reward=1.0, learning_rate=0.1)
        before = net.connections["edge"].weight
        changes = modulator.update(net, reward=-1.0, learning_rate=0.1)
        self.assertLess(changes["edge"], 0.0)
        self.assertLess(net.connections["edge"].weight, before)

    def test_weight_bounds_and_disabled_edges(self):
        net = self.make_network()
        modulator = RewardModulator()
        net.connections["edge"].weight = 1.99
        modulator.update(net, reward=1.0, learning_rate=100.0)
        self.assertEqual(net.connections["edge"].weight, 2.0)
        net.connections["edge"].enabled = False
        self.assertEqual(modulator.update(net, reward=10.0), {})

    def test_snapshot_round_trip(self):
        modulator = RewardModulator(trace_decay=0.7, baseline_rate=0.2)
        net = self.make_network()
        modulator.update(net, reward=0.25)
        restored = RewardModulator.from_snapshot(modulator.snapshot())
        self.assertEqual(restored.snapshot(), modulator.snapshot())

    def test_invalid_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            RewardModulator(trace_decay=1.1)
        with self.assertRaises(ValueError):
            RewardModulator(baseline_rate=0.0)
        with self.assertRaises(ValueError):
            RewardModulator().update(self.make_network(), reward=float("nan"))


if __name__ == "__main__":
    unittest.main()
