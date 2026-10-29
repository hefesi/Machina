"""Tests for outcome-based MNN memory retrieval feedback."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_memory_retrieval_feedback import MNNMemoryRetrievalFeedback


class MNNMemoryRetrievalFeedbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "memory.sqlite3"
        self.memory = FragmentMemory(self.path)
        self.memory.add(
            "Validated design decision",
            source_uri="test://decision",
            importance=0.5,
            confidence=0.9,
            pinned=True,
            tags=["architecture"],
            fragment_id="decision",
        )
        self.feedback = MNNMemoryRetrievalFeedback(self.memory)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def test_positive_feedback_increases_importance(self) -> None:
        updated, event = self.feedback.apply("decision", useful=True)
        self.assertAlmostEqual(0.6, updated.importance)
        self.assertAlmostEqual(0.5, event.importance_before)
        self.assertAlmostEqual(0.6, event.importance_after)
        self.assertTrue(updated.pinned)

    def test_negative_feedback_changes_relevance_not_truth_or_content(self) -> None:
        updated, event = self.feedback.apply("decision", useful=False, strength=0.2)
        self.assertAlmostEqual(0.3, updated.importance)
        self.assertEqual(0.9, updated.confidence)
        self.assertEqual("Validated design decision", updated.content)
        self.assertEqual("test://decision", updated.source_uri)
        self.assertTrue(updated.pinned)
        self.assertFalse(event.useful)

    def test_feedback_persists_after_reopening_database(self) -> None:
        self.feedback.apply("decision", useful=True)
        self.memory.close()
        self.memory = FragmentMemory(self.path)
        self.assertAlmostEqual(0.6, self.memory.get("decision", record_access=False).importance)

    def test_importance_is_bounded(self) -> None:
        self.memory.reinforce("decision", importance_delta=0.49)
        updated, _ = self.feedback.apply("decision", useful=True, strength=0.9)
        self.assertEqual(1.0, updated.importance)
        updated, _ = self.feedback.apply("decision", useful=False, strength=1.0)
        self.assertEqual(0.0, updated.importance)

    def test_batch_feedback_updates_each_explicit_fragment(self) -> None:
        self.memory.add(
            "Secondary memory", source_uri="test://secondary",
            importance=0.4, fragment_id="secondary",
        )
        results = self.feedback.apply_many(
            {"decision": True, "secondary": False}, strength=0.2
        )
        self.assertEqual(["decision", "secondary"], [event.fragment_id for _, event in results])
        self.assertAlmostEqual(0.7, self.memory.get("decision", record_access=False).importance)
        self.assertAlmostEqual(0.2, self.memory.get("secondary", record_access=False).importance)

    def test_batch_with_unknown_id_changes_nothing(self) -> None:
        self.memory.add(
            "Secondary memory", source_uri="test://secondary",
            importance=0.4, fragment_id="secondary",
        )
        with self.assertRaises(KeyError):
            self.feedback.apply_many({"decision": True, "missing": False})
        self.assertAlmostEqual(0.5, self.memory.get("decision", record_access=False).importance)
        self.assertAlmostEqual(0.4, self.memory.get("secondary", record_access=False).importance)

    def test_batch_rejects_non_boolean_label_before_updates(self) -> None:
        with self.assertRaises(ValueError):
            self.feedback.apply_many({"decision": True, "bad": 1})
        self.assertAlmostEqual(0.5, self.memory.get("decision", record_access=False).importance)

    def test_feedback_id_is_idempotent_across_retries(self) -> None:
        first = self.feedback.apply_many(
            {"decision": True}, strength=0.2, feedback_id="cycle-123"
        )
        second = self.feedback.apply_many(
            {"decision": True}, strength=0.2, feedback_id="cycle-123"
        )
        self.assertAlmostEqual(0.7, first[0][0].importance)
        self.assertAlmostEqual(0.7, second[0][0].importance)
        self.assertAlmostEqual(0.5, second[0][1].importance_before)
        self.assertAlmostEqual(0.7, second[0][1].importance_after)
        self.assertAlmostEqual(0.7, self.memory.get("decision", record_access=False).importance)

    def test_feedback_idempotency_survives_database_reopen(self) -> None:
        self.feedback.apply_many(
            {"decision": True}, strength=0.2, feedback_id="durable-cycle-123"
        )
        self.memory.close()
        self.memory = FragmentMemory(self.path)
        self.feedback = MNNMemoryRetrievalFeedback(self.memory)
        retried = self.feedback.apply_many(
            {"decision": True}, strength=0.2, feedback_id="durable-cycle-123"
        )
        self.assertAlmostEqual(0.7, retried[0][0].importance)
        self.assertAlmostEqual(0.5, retried[0][1].importance_before)
        self.assertAlmostEqual(0.7, retried[0][1].importance_after)

    def test_feedback_id_cannot_be_reused_with_different_payload(self) -> None:
        self.feedback.apply_many(
            {"decision": True}, strength=0.2, feedback_id="cycle-123"
        )
        with self.assertRaises(ValueError):
            self.feedback.apply_many(
                {"decision": False}, strength=0.2, feedback_id="cycle-123"
            )
        self.assertAlmostEqual(0.7, self.memory.get("decision", record_access=False).importance)

    def test_idempotent_batch_with_missing_id_changes_nothing(self) -> None:
        with self.assertRaises(KeyError):
            self.feedback.apply_many(
                {"decision": True, "missing": False},
                strength=0.2,
                feedback_id="cycle-missing",
            )
        self.assertAlmostEqual(0.5, self.memory.get("decision", record_access=False).importance)

    def test_empty_batch_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.feedback.apply_many({})

    def test_invalid_feedback_is_rejected(self) -> None:
        for kwargs in (
            {"useful": 1},
            {"useful": True, "strength": -0.1},
            {"useful": False, "strength": float("nan")},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.feedback.apply("decision", **kwargs)

    def test_unknown_fragment_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            self.feedback.apply("missing", useful=True)


if __name__ == "__main__":
    unittest.main()
