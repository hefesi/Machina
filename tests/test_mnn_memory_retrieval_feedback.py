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
