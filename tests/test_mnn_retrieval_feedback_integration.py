"""Integration test: retrieval feedback changes future recall ranking."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_memory_retrieval_feedback import MNNMemoryRetrievalFeedback


class RetrievalFeedbackIntegrationTests(unittest.TestCase):
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
