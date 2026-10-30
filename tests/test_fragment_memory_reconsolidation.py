"""Tests for evidence-backed, version-preserving memory reconsolidation."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory


class FragmentMemoryReconsolidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp.name) / "memory.sqlite3")
        self.original = self.memory.add(
            "The first interpretation", source_uri="test://experience",
            confidence=0.6, fragment_id="experience",
        )

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_revision_preserves_prior_content_and_updates_current_memory(self):
        current, revision, applied = self.memory.reconsolidate(
            "experience", revised_content="Updated interpretation",
            evidence_id="evidence-2", operation_id="revision-1", confidence=0.9,
        )
        self.assertTrue(applied)
        self.assertEqual("Updated interpretation", current.content)
        self.assertEqual(0.9, current.confidence)
        self.assertEqual("The first interpretation", revision["prior_content"])
        history = self.memory.revision_history("experience")
        self.assertEqual(1, len(history))
        self.assertEqual("The first interpretation", history[0]["prior_content"])

    def test_retry_is_idempotent(self):
        args = dict(
            revised_content="Updated interpretation",
            evidence_id="evidence-2", operation_id="revision-1", confidence=0.9,
        )
        self.memory.reconsolidate("experience", **args)
        current, _, applied = self.memory.reconsolidate("experience", **args)
        self.assertFalse(applied)
        self.assertEqual("Updated interpretation", current.content)
        self.assertEqual(1, len(self.memory.revision_history("experience")))

    def test_operation_id_cannot_be_reused_for_different_revision(self):
        self.memory.reconsolidate(
            "experience", revised_content="Updated interpretation",
            evidence_id="evidence-2", operation_id="revision-1",
        )
        with self.assertRaises(ValueError):
            self.memory.reconsolidate(
                "experience", revised_content="Different update",
                evidence_id="evidence-3", operation_id="revision-1",
            )

    def test_invalid_revision_does_not_mutate_memory(self):
        with self.assertRaises(ValueError):
            self.memory.reconsolidate(
                "experience", revised_content=" ", evidence_id="e",
                operation_id="bad",
            )
        current = self.memory.get("experience", record_access=False)
        self.assertEqual(self.original.content, current.content)
        self.assertEqual([], self.memory.revision_history("experience"))

    def test_unknown_fragment_is_rejected(self):
        with self.assertRaises(KeyError):
            self.memory.reconsolidate(
                "missing", revised_content="Updated",
                evidence_id="e", operation_id="op",
            )


if __name__ == "__main__":
    unittest.main()
