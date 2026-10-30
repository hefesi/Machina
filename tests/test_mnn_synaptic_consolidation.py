import unittest

from machina.mnn import Connection, MNN, Unit
from machina.mnn_synaptic_consolidation import MNNSynapticConsolidator


class MNNSynapticConsolidatorTests(unittest.TestCase):
    def setUp(self):
        self.network = MNN()
        self.network.add_unit(Unit("a", activation="identity", state=1.0))
        self.network.add_unit(Unit("b", activation="identity", state=1.0))
        self.network.add_connection(Connection("stable", "a", "b", 1.0))
        self.network.add_connection(Connection("unused", "b", "a", 1.0))
        self.consolidator = MNNSynapticConsolidator(consolidation_observations=3)

    def test_repeated_evidence_protects_connection_from_explicit_decay(self):
        for index in range(3):
            self.assertTrue(self.consolidator.record_reinforcement(
                self.network, ["stable"], evidence_id=f"e-{index}",
                operation_id=f"op-{index}",
            ))
        self.assertEqual(1.0, self.consolidator.stability("stable"))
        before_stable = self.network.connections["stable"].weight
        before_unused = self.network.connections["unused"].weight
        changes = self.consolidator.apply_decay(self.network, decay_rate=0.2)
        self.assertEqual(0.0, changes["stable"])
        self.assertEqual(before_stable, self.network.connections["stable"].weight)
        self.assertLess(self.network.connections["unused"].weight, before_unused)

    def test_partial_stability_attenuates_decay(self):
        self.consolidator.record_reinforcement(
            self.network, ["stable"], evidence_id="e-1", operation_id="op-1"
        )
        changes = self.consolidator.apply_decay(self.network, decay_rate=0.3)
        self.assertAlmostEqual(-0.2, changes["stable"])
        self.assertAlmostEqual(-0.3, changes["unused"])

    def test_operation_retry_is_idempotent(self):
        first = self.consolidator.record_reinforcement(
            self.network, ["stable"], evidence_id="e-1", operation_id="same"
        )
        second = self.consolidator.record_reinforcement(
            self.network, ["stable"], evidence_id="e-1", operation_id="same"
        )
        self.assertTrue(first)
        self.assertFalse(second)
        self.assertEqual(1, self.consolidator.reinforcement_counts["stable"])

    def test_invalid_evidence_does_not_partially_mutate_state(self):
        with self.assertRaises(ValueError):
            self.consolidator.record_reinforcement(
                self.network, ["stable", "missing"],
                evidence_id="e-1", operation_id="bad",
            )
        self.assertEqual({}, self.consolidator.reinforcement_counts)
        self.assertEqual(set(), self.consolidator._operations)

    def test_decay_is_explicit_and_never_prunes_edges(self):
        before = self.network.snapshot()
        self.assertEqual(2, len(self.network.connections))
        self.assertEqual(before, self.network.snapshot())
        self.consolidator.apply_decay(self.network, decay_rate=0.1)
        self.assertEqual(2, len(self.network.connections))

    def test_snapshot_round_trip_preserves_evidence_and_idempotency(self):
        self.consolidator.record_reinforcement(
            self.network, ["stable"], evidence_id="e-1", operation_id="op-1"
        )
        restored = MNNSynapticConsolidator.from_snapshot(self.consolidator.snapshot())
        self.assertEqual(self.consolidator.snapshot(), restored.snapshot())
        self.assertFalse(restored.record_reinforcement(
            self.network, ["stable"], evidence_id="e-1", operation_id="op-1"
        ))

    def test_invalid_decay_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            self.consolidator.apply_decay(self.network, decay_rate=1.1)
        with self.assertRaises(ValueError):
            self.consolidator.apply_decay(self.network, decay_rate=0.1, protected_stability=-0.1)


if __name__ == "__main__":
    unittest.main()
