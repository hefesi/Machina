"""Integration test: retrieval feedback changes future recall ranking."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_memory_retrieval_feedback import MNNMemoryRetrievalFeedback


class RetrievalFeedbackIntegrationTests(unittest.TestCase):
    def test_feedback_ranking_survives_database_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "memory.sqlite3"
            with FragmentMemory(path) as memory:
                memory.add(
                    "alpha beta task memory",
                    source_uri="test://target",
                    importance=0.1,
                    confidence=0.5,
                    fragment_id="target",
                )
                memory.add(
                    "alpha beta task memory",
                    source_uri="test://competitor",
                    importance=0.2,
                    confidence=0.5,
                    fragment_id="competitor",
                )
                MNNMemoryRetrievalFeedback(memory).apply(
                    "target", useful=True, strength=0.9, feedback_id="experiment-1"
                )
                expected = [item.id for item in memory.recall("alpha beta task", limit=2)]
                self.assertEqual(["target", "competitor"], expected)

            with FragmentMemory(path) as restarted:
                actual = [item.id for item in restarted.recall("alpha beta task", limit=2)]
                self.assertEqual(expected, actual)
                self.assertAlmostEqual(1.0, restarted.get("target", record_access=False).importance)
                self.assertEqual(2, restarted.count())

    def test_negative_feedback_does_not_demote_pinned_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "memory.sqlite3"
            with FragmentMemory(path) as memory:
                memory.add(
                    "critical emergency shutdown procedure",
                    source_uri="test://critical",
                    importance=0.8,
                    confidence=1.0,
                    pinned=True,
                    fragment_id="critical",
                )
                memory.add(
                    "routine maintenance note",
                    source_uri="test://routine",
                    importance=0.6,
                    confidence=0.7,
                    fragment_id="routine",
                )
                result = MNNMemoryRetrievalFeedback(memory).apply(
                    "critical", useful=False, strength=0.5, feedback_id="pinned-negative"
                )
                self.assertEqual(0.8, result[0].importance)
                self.assertTrue(result[0].pinned)

                # The non-idempotent API must preserve the same protection.
                direct = MNNMemoryRetrievalFeedback(memory).apply(
                    "critical", useful=False, strength=0.5
                )
                self.assertEqual(0.8, direct[0].importance)
                self.assertEqual(
                    "critical",
                    memory.active(limit=1)[0].id,
                )

    def test_successful_feedback_can_change_recall_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "memory.sqlite3"
            with FragmentMemory(path) as memory:
                memory.add(
                    "alpha beta task memory",
                    source_uri="test://target",
                    importance=0.1,
                    confidence=0.5,
                    fragment_id="target",
                )
                memory.add(
                    "alpha beta task memory",
                    source_uri="test://competitor",
                    importance=0.2,
                    confidence=0.5,
                    fragment_id="competitor",
                )

                before = [item.id for item in memory.recall("alpha beta task", limit=2)]
                self.assertEqual(["competitor", "target"], before)

                feedback = MNNMemoryRetrievalFeedback(memory)
                feedback.apply("target", useful=True, strength=0.9)

                after = [item.id for item in memory.recall("alpha beta task", limit=2)]
                self.assertEqual(["target", "competitor"], after)

                # Feedback changes ranking, not the remembered content.
                self.assertEqual(
                    "alpha beta task memory",
                    memory.get("target", record_access=False).content,
                )


if __name__ == "__main__":
    unittest.main()
