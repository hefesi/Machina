import tempfile
import unittest
from pathlib import Path

from machina.brain import VirtualBrain
from machina.event_store import EventStore
from machina.mnn_strategy_event_bridge import MNNStrategyEventBridge


class MNNStrategyEventBridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = EventStore(Path(self.tmp.name) / "events.db")
        self.addCleanup(self.store.close)
        self.cycle_id = "cycle-strategy-test"
        self.store.create_cycle(self.cycle_id)
        self.bridge = MNNStrategyEventBridge(self.store)
        self.proposal = {
            "status": "proposed",
            "action": "candidate-A",
            "context": " workload A ",
            "evidence_ids": [" evidence-1 "],
        }

    def test_proposal_and_confirmed_outcome_form_causal_event_chain(self):
        proposal = self.bridge.record_proposal(
            self.cycle_id, self.proposal,
            expected_reward=0.6, proposal_id="proposal-1",
        )
        self.assertFalse(proposal.artifact.data["executed"])
        outcome = self.bridge.record_outcome(
            self.cycle_id, "proposal-1",
            execution_confirmed=True, executed_action="candidate-A",
            observed_reward=0.9, operation_id="operation-1",
        )
        self.assertEqual(proposal.artifact.id, outcome.artifact.input_refs[0])
        self.assertEqual(proposal.artifact.id, outcome.causation_id)
        self.assertAlmostEqual(0.3, outcome.artifact.data["prediction_error"])
        self.store.verify_integrity()

    def test_stable_ids_make_sequential_retries_idempotent(self):
        first = self.bridge.record_proposal(
            self.cycle_id, self.proposal,
            expected_reward=0.6, proposal_id="proposal-2",
        )
        second = self.bridge.record_proposal(
            self.cycle_id, self.proposal,
            expected_reward=0.6, proposal_id="proposal-2",
        )
        self.assertEqual(first.event_id, second.event_id)
        first_outcome = self.bridge.record_outcome(
            self.cycle_id, "proposal-2",
            execution_confirmed=True, executed_action="candidate-A",
            observed_reward=0.7, operation_id="operation-2",
        )
        second_outcome = self.bridge.record_outcome(
            self.cycle_id, "proposal-2",
            execution_confirmed=True, executed_action="candidate-A",
            observed_reward=0.7, operation_id="operation-2",
        )
        self.assertEqual(first_outcome.event_id, second_outcome.event_id)
        self.assertEqual(1, len(self.bridge.outcomes_for("proposal-2")))

    def test_changed_payload_cannot_reuse_stable_identifiers(self):
        self.bridge.record_proposal(
            self.cycle_id, self.proposal,
            expected_reward=0.6, proposal_id="proposal-3",
        )
        with self.assertRaises(ValueError):
            self.bridge.record_proposal(
                self.cycle_id, self.proposal,
                expected_reward=0.8, proposal_id="proposal-3",
            )
        self.bridge.record_outcome(
            self.cycle_id, "proposal-3",
            execution_confirmed=True, executed_action="candidate-A",
            observed_reward=0.7, operation_id="operation-3",
        )
        with self.assertRaises(ValueError):
            self.bridge.record_outcome(
                self.cycle_id, "proposal-3",
                execution_confirmed=True, executed_action="candidate-A",
                observed_reward=0.8, operation_id="operation-3",
            )

    def test_unconfirmed_or_mismatched_execution_is_rejected(self):
        self.bridge.record_proposal(
            self.cycle_id, self.proposal,
            expected_reward=0.6, proposal_id="proposal-4",
        )
        with self.assertRaises(ValueError):
            self.bridge.record_outcome(
                self.cycle_id, "proposal-4",
                execution_confirmed=False, executed_action="candidate-A",
                observed_reward=0.7, operation_id="operation-4",
            )
        with self.assertRaises(ValueError):
            self.bridge.record_outcome(
                self.cycle_id, "proposal-4",
                execution_confirmed=True, executed_action="other",
                observed_reward=0.7, operation_id="operation-4",
            )

    def test_abstention_is_recorded_but_cannot_receive_outcome(self):
        self.bridge.record_proposal(
            self.cycle_id,
            {"status": "abstain", "action": None, "context": "workload A"},
            expected_reward=0.4, proposal_id="proposal-abstain",
        )
        with self.assertRaises(ValueError):
            self.bridge.record_outcome(
                self.cycle_id, "proposal-abstain",
                execution_confirmed=True, executed_action="candidate-A",
                observed_reward=0.7, operation_id="operation-abstain",
            )

    def test_malformed_evidence_is_rejected_before_append(self):
        for evidence_ids in ("evidence-1", ["", "evidence-2"], ["evidence-1", "evidence-1"]):
            with self.subTest(evidence_ids=evidence_ids):
                with self.assertRaises(ValueError):
                    self.bridge.record_proposal(
                        self.cycle_id,
                        dict(self.proposal, evidence_ids=evidence_ids),
                        expected_reward=0.6,
                        proposal_id="bad-evidence",
                    )
        self.assertEqual([], self.store.events_for_cycle(self.cycle_id))

    def test_virtual_brain_exposes_the_event_bridge(self):
        brain_path = Path(self.tmp.name) / "brain.db"
        with VirtualBrain(brain_path) as brain:
            cycle_id = brain.start_cycle("observation", "objective")
            event = brain.strategy_events.record_proposal(
                cycle_id, self.proposal,
                expected_reward=0.5, proposal_id="brain-proposal",
            )
            self.assertEqual(cycle_id, event.cycle_id)
            brain.store.verify_integrity()


if __name__ == "__main__":
    unittest.main()
