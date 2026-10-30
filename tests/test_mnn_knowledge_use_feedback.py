"""Tests for execution-confirmed, context-specific knowledge-use feedback."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from machina.fragment_memory import FragmentMemory
from machina.mnn_knowledge_use_feedback import MNNKnowledgeUseFeedback

class MNNKnowledgeUseFeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp_dir.name) / "feedback.sqlite3")
        self.memory.add("Evidence one", source_uri="test://one", fragment_id="e1")
        self.memory.add("Evidence two", source_uri="test://two", fragment_id="e2")
        self.adapter = MNNKnowledgeUseFeedback(self.memory, strength=0.2)
        self.proposal = {
            "status": "proposed", "action": "use-plan-A", "context": "Project Alpha",
            "evidence_ids": ["e1", "e2"],
        }

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def apply_feedback(self, **kwargs):
        return self.adapter.apply(
            self.proposal, {"e1": True, "e2": False},
            execution_confirmed=True, executed_action="use-plan-A",
            operation_id="outcome-001", **kwargs,
        )

    def test_explicit_labels_update_only_the_given_context(self) -> None:
        result = self.apply_feedback()
        self.assertTrue(result.applied)
        self.assertEqual("project alpha", result.context)
        self.assertAlmostEqual(0.7, self.memory.context_importance("e1", "Project Alpha"))
        self.assertAlmostEqual(0.3, self.memory.context_importance("e2", "Project Alpha"))
        self.assertAlmostEqual(0.5, self.memory.context_importance("e1", "Project Beta"))

    def test_retry_is_idempotent(self) -> None:
        first = self.apply_feedback()
        second = self.apply_feedback()
        self.assertTrue(first.applied)
        self.assertFalse(second.applied)
        self.assertEqual(first.scores, second.scores)
        self.assertAlmostEqual(0.7, self.memory.context_importance("e1", "Project Alpha"))

    def test_unconfirmed_execution_is_rejected_without_writes(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.apply(self.proposal, {"e1": True}, execution_confirmed=False,
                               executed_action="use-plan-A", operation_id="x")
        self.assertAlmostEqual(0.5, self.memory.context_importance("e1", "Project Alpha"))

    def test_mismatched_action_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.apply(self.proposal, {"e1": True}, execution_confirmed=True,
                               executed_action="different", operation_id="x")

    def test_cannot_label_uncited_evidence(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.apply(self.proposal, {"not-cited": True}, execution_confirmed=True,
                               executed_action="use-plan-A", operation_id="x")

    def test_non_boolean_labels_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.adapter.apply(self.proposal, {"e1": 1}, execution_confirmed=True,
                               executed_action="use-plan-A", operation_id="x")

    def test_operation_id_cannot_be_reused_with_changed_labels(self) -> None:
        self.apply_feedback()
        with self.assertRaises(ValueError):
            self.adapter.apply(self.proposal, {"e1": False}, execution_confirmed=True,
                               executed_action="use-plan-A", operation_id="outcome-001")

if __name__ == "__main__":
    unittest.main()
