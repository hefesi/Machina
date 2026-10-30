import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_strategy_outcome_journal import MNNStrategyOutcomeJournal


class StrategyOutcomeJournalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "journal.db"
        self.memory = FragmentMemory(self.path)
        self.addCleanup(self.memory.close)
        self.journal = MNNStrategyOutcomeJournal(self.memory)
        self.proposal = {
            "status": "proposed", "action": "candidate",
            "context": "workload A", "evidence_ids": ["evidence-1"],
        }

    def test_proposal_is_not_an_execution_and_outcome_is_separate(self):
        proposal = self.journal.record_proposal(
            self.proposal, expected_reward=0.7, proposal_id="p-1"
        )
        self.assertFalse(proposal.metadata["executed"])
        outcome = self.journal.record_outcome(
            "p-1", execution_confirmed=True, executed_action="candidate",
            observed_reward=0.9, operation_id="o-1",
        )
        self.assertAlmostEqual(0.2, outcome.metadata["prediction_error"])
        self.assertEqual(proposal.id, outcome.related_ids[0])

    def test_abstention_can_be_recorded_but_cannot_receive_outcome(self):
        self.journal.record_proposal(
            {"status": "abstain", "action": None, "context": "workload A"},
            expected_reward=0.5, proposal_id="p-abstain",
        )
        with self.assertRaises(ValueError):
            self.journal.record_outcome(
                "p-abstain", execution_confirmed=True, executed_action="candidate",
                observed_reward=0.8, operation_id="o-abstain",
            )

    def test_unconfirmed_or_mismatched_execution_is_rejected(self):
        self.journal.record_proposal(
            self.proposal, expected_reward=0.5, proposal_id="p-2"
        )
        with self.assertRaises(ValueError):
            self.journal.record_outcome(
                "p-2", execution_confirmed=False, executed_action="candidate",
                observed_reward=0.8, operation_id="o-2",
            )
        with self.assertRaises(ValueError):
            self.journal.record_outcome(
                "p-2", execution_confirmed=True, executed_action="other",
                observed_reward=0.8, operation_id="o-2",
            )

    def test_retries_are_idempotent_and_changed_payload_is_rejected(self):
        first = self.journal.record_proposal(
            self.proposal, expected_reward=0.5, proposal_id="p-3"
        )
        repeated = self.journal.record_proposal(
            self.proposal, expected_reward=0.5, proposal_id="p-3"
        )
        self.assertEqual(first.id, repeated.id)
        with self.assertRaises(ValueError):
            self.journal.record_proposal(
                self.proposal, expected_reward=0.6, proposal_id="p-3"
            )
        first_outcome = self.journal.record_outcome(
            "p-3", execution_confirmed=True, executed_action="candidate",
            observed_reward=0.8, operation_id="o-3",
        )
        repeated_outcome = self.journal.record_outcome(
            "p-3", execution_confirmed=True, executed_action="candidate",
            observed_reward=0.8, operation_id="o-3",
        )
        self.assertEqual(first_outcome.id, repeated_outcome.id)
        with self.assertRaises(ValueError):
            self.journal.record_outcome(
                "p-3", execution_confirmed=True, executed_action="candidate",
                observed_reward=0.9, operation_id="o-3",
            )

    def test_records_survive_reopening_database(self):
        self.journal.record_proposal(
            self.proposal, expected_reward=0.4, proposal_id="p-4"
        )
        self.journal.record_outcome(
            "p-4", execution_confirmed=True, executed_action="candidate",
            observed_reward=0.6, operation_id="o-4",
        )
        self.memory.close()
        self.memory = FragmentMemory(self.path)
        self.journal = MNNStrategyOutcomeJournal(self.memory)
        outcomes = self.journal.outcomes_for("p-4")
        self.assertEqual(1, len(outcomes))
        self.assertAlmostEqual(0.2, outcomes[0].metadata["prediction_error"])


    def test_invalid_evidence_ids_are_rejected(self):
        invalid_values = [
            "evidence-1",
            ["evidence-1", ""],
            ["evidence-1", 7],
            ["evidence-1", "evidence-1"],
            None,
        ]
        for evidence_ids in invalid_values:
            with self.subTest(evidence_ids=evidence_ids):
                proposal = dict(self.proposal, evidence_ids=evidence_ids)
                with self.assertRaises(ValueError):
                    self.journal.record_proposal(
                        proposal, expected_reward=0.5, proposal_id="invalid-evidence"
                    )

    def test_unhashable_status_is_reported_as_validation_error(self):
        proposal = dict(self.proposal, status=["proposed"])
        with self.assertRaisesRegex(ValueError, "proposal status"):
            self.journal.record_proposal(
                proposal, expected_reward=0.5, proposal_id="invalid-status"
            )

    def test_evidence_ids_are_normalized_before_persistence(self):
        proposal = dict(self.proposal, evidence_ids=[" evidence-1 ", "evidence-2"])
        stored = self.journal.record_proposal(
            proposal, expected_reward=0.5, proposal_id="normalized-evidence"
        )
        self.assertEqual(["evidence-1", "evidence-2"], stored.metadata["evidence_ids"])


if __name__ == "__main__":
    unittest.main()
