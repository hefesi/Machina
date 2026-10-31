import unittest

from machina.mnn import Connection, MNN, Unit
from machina.mnn_plasticity_control import MNNPlasticityController


class MNNPlasticityControllerTests(unittest.TestCase):
    def setUp(self):
        self.network = MNN(weight_limit=2.0)
        self.network.add_unit(Unit("pre", activation="identity", state=0.8))
        self.network.add_unit(Unit("post", activation="identity", state=0.5))
        self.network.add_connection(Connection("edge", "pre", "post", 0.4))
        self.network.add_connection(Connection("disabled", "post", "pre", 0.2, enabled=False))
        self.controller = MNNPlasticityController()

    def test_proposal_is_bounded_and_does_not_mutate_network(self):
        before = self.network.snapshot()
        proposal = self.controller.propose_hebbian(
            self.network, proposal_id="p-1", learning_rate=1.0, reward=1.0, max_delta=0.03
        )
        self.assertEqual(before, self.network.snapshot())
        self.assertAlmostEqual(0.03, proposal.deltas["edge"])
        self.assertEqual(0.0, proposal.deltas["disabled"])

    def test_apply_requires_explicit_call_and_rollback_restores_weights(self):
        proposal = self.controller.propose_hebbian(
            self.network, proposal_id="p-2", learning_rate=0.1, reward=1.0
        )
        before = self.network.connections["edge"].weight
        self.controller.apply(self.network, proposal)
        self.assertGreater(self.network.connections["edge"].weight, before)
        self.controller.rollback(self.network, "p-2")
        self.assertEqual(before, self.network.connections["edge"].weight)

    def test_stale_weight_rejects_entire_proposal_without_partial_changes(self):
        proposal = self.controller.propose_hebbian(
            self.network, proposal_id="p-3", learning_rate=0.1, reward=1.0
        )
        self.network.connections["disabled"].weight = 0.25
        before = {key: edge.weight for key, edge in self.network.connections.items()}
        with self.assertRaises(ValueError):
            self.controller.apply(self.network, proposal)
        self.assertEqual(before, {key: edge.weight for key, edge in self.network.connections.items()})

    def test_topology_change_rejects_proposal(self):
        proposal = self.controller.propose_hebbian(
            self.network, proposal_id="p-4", learning_rate=0.1, reward=1.0
        )
        self.network.add_unit(Unit("extra"))
        with self.assertRaises(ValueError):
            self.controller.apply(self.network, proposal)

    def test_rollback_refuses_to_overwrite_later_learning(self):
        proposal = self.controller.propose_hebbian(
            self.network, proposal_id="p-5", learning_rate=0.1, reward=1.0
        )
        self.controller.apply(self.network, proposal)
        self.network.connections["edge"].weight += 0.01
        with self.assertRaises(ValueError):
            self.controller.rollback(self.network, "p-5")

    def test_snapshot_preserves_rollback_guard(self):
        proposal = self.controller.propose_hebbian(
            self.network, proposal_id="p-6", learning_rate=0.1, reward=1.0
        )
        self.controller.apply(self.network, proposal)
        restored = MNNPlasticityController.from_snapshot(self.controller.snapshot())
        restored.rollback(self.network, "p-6")
        self.assertAlmostEqual(0.4, self.network.connections["edge"].weight)

    def test_invalid_inputs_are_rejected(self):
        for reward in (-0.1, 1.1, True):
            with self.assertRaises(ValueError):
                self.controller.propose_hebbian(
                    self.network, proposal_id=f"bad-{reward}", learning_rate=0.1, reward=reward
                )
        with self.assertRaises(ValueError):
            self.controller.propose_hebbian(
                self.network, proposal_id="bad-rate", learning_rate=-0.1, reward=0.5
            )


if __name__ == "__main__":
    unittest.main()
