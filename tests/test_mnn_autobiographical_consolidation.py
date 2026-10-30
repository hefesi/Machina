import unittest

from machina.mnn import Connection, MNN, Unit
from machina.mnn_autobiographical_learning import AutobiographicalLearningSignal
from machina.mnn_autobiographical_consolidation import MNNAutobiographicalConsolidationAdapter
from machina.mnn_synaptic_consolidation import MNNSynapticConsolidator


class MNNAutobiographicalConsolidationAdapterTests(unittest.TestCase):
    def setUp(self):
        self.network = MNN()
        self.network.add_unit(Unit("a"))
        self.network.add_unit(Unit("b"))
        self.network.add_connection(Connection("a-b", "a", "b", 0.4))
        self.consolidator = MNNSynapticConsolidator()
        self.adapter = MNNAutobiographicalConsolidationAdapter()
        self.signal = AutobiographicalLearningSignal(
            transformation_event_id="transform:1",
            changed_paths=("capability.reasoning",),
            observation_count=5,
            mean_outcome=0.9,
            mean_absolute_prediction_error=0.1,
            evidence_refs=("episode:1", "episode:2"),
            recommendation="candidate_for_reinforcement",
            rationale="Positive observed outcomes and calibrated predictions.",
        )

    def test_explicit_acceptance_records_evidence_without_changing_weights(self):
        initial = self.network.connections["a-b"].weight
        applied = self.adapter.record(
            self.signal, self.network, self.consolidator, ["a-b"],
            evidence_id="episode:1", operation_id="review:1",
            accepted_for_reinforcement=True,
        )
        self.assertTrue(applied)
        self.assertEqual(initial, self.network.connections["a-b"].weight)
        self.assertEqual(1, self.consolidator.reinforcement_counts["a-b"])

    def test_rejected_signal_cannot_be_recorded(self):
        with self.assertRaisesRegex(ValueError, "explicitly accepted"):
            self.adapter.record(
                self.signal, self.network, self.consolidator, ["a-b"],
                evidence_id="episode:1", operation_id="review:2",
                accepted_for_reinforcement=False,
            )

    def test_non_candidate_signal_cannot_be_recorded(self):
        from dataclasses import replace
        signal = replace(self.signal, recommendation="review_or_revise")
        with self.assertRaisesRegex(ValueError, "only reinforcement-candidate"):
            self.adapter.record(
                signal, self.network, self.consolidator, ["a-b"],
                evidence_id="episode:1", operation_id="review:3",
                accepted_for_reinforcement=True,
            )

    def test_evidence_must_be_linked_to_signal(self):
        with self.assertRaisesRegex(ValueError, "belong to"):
            self.adapter.record(
                self.signal, self.network, self.consolidator, ["a-b"],
                evidence_id="unrelated", operation_id="review:4",
                accepted_for_reinforcement=True,
            )

    def test_operation_retry_is_idempotent(self):
        args = (self.signal, self.network, self.consolidator, ["a-b"])
        kwargs = dict(evidence_id="episode:1", operation_id="review:5",
                      accepted_for_reinforcement=True)
        self.assertTrue(self.adapter.record(*args, **kwargs))
        self.assertFalse(self.adapter.record(*args, **kwargs))
        self.assertEqual(1, self.consolidator.reinforcement_counts["a-b"])


if __name__ == "__main__":
    unittest.main()
