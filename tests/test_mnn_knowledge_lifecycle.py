"""Tests for the non-destructive MNN knowledge lifecycle."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from machina.fragment_memory import FragmentMemory
from machina.mnn_knowledge_lifecycle import MNNKnowledgeLifecycle

class MNNKnowledgeLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp_dir.name) / "lifecycle.sqlite3")
        self.lifecycle = MNNKnowledgeLifecycle(self.memory, min_support=2)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def add(self, identifier: str, polarity: str = "supports") -> None:
        self.memory.add(
            f"Observation {identifier}", source_uri=f"test://{identifier}",
            tags=["shared-pattern"], confidence=0.8,
            metadata={"polarity": polarity}, fragment_id=identifier,
        )

    def test_run_discovers_materializes_and_audits(self) -> None:
        self.add("a")
        self.add("b")
        result = self.lifecycle.run()
        self.assertEqual(1, len(result.hypotheses))
        self.assertEqual(1, len(result.materialized_concepts))
        self.assertTrue(result.audit_fragments)
        self.assertEqual("current", result.reviews_after_refresh[0].state)

    def test_repeated_run_is_idempotent(self) -> None:
        self.add("a")
        self.add("b")
        first = self.lifecycle.run()
        count = self.memory.count()
        second = self.lifecycle.run()
        self.assertEqual(count, self.memory.count())
        self.assertEqual([item.id for item in first.materialized_concepts],
                         [item.id for item in second.materialized_concepts])
        self.assertEqual([item.id for item in first.audit_fragments],
                         [item.id for item in second.audit_fragments])

    def test_observational_run_does_not_write(self) -> None:
        self.add("a")
        self.add("b")
        count = self.memory.count()
        result = self.lifecycle.run(refresh=False, persist_audit=False)
        self.assertEqual(count, self.memory.count())
        self.assertEqual(1, len(result.hypotheses))
        self.assertEqual((), result.materialized_concepts)
        self.assertEqual((), result.audit_fragments)

    def test_new_conflicting_evidence_is_reported(self) -> None:
        self.add("a")
        self.add("b")
        self.lifecycle.run()
        self.add("counter", "contradicts")
        result = self.lifecycle.run()
        self.assertGreaterEqual(result.conflicted_count, 1)

    def test_invalid_flags_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.lifecycle.run(refresh=1)
        with self.assertRaises(ValueError):
            self.lifecycle.run(persist_audit="yes")

if __name__ == "__main__":
    unittest.main()
