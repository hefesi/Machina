"""Tests for explicit, append-only relations between concept hypotheses."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_concept_relations import MNNConceptRelationStore


class MNNConceptRelationStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp_dir.name) / "relations.sqlite3")
        self.memory.add("Evidence A", fragment_id="evidence-a", tags=("a",))
        self.memory.add("Evidence B", fragment_id="evidence-b", tags=("b",))
        self.memory.add("Concept A", kind="concept", fragment_id="concept-a")
        self.memory.add("Concept B", kind="concept", fragment_id="concept-b")
        self.store = MNNConceptRelationStore(self.memory)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def test_persists_explicit_competing_relation_with_provenance(self) -> None:
        relation = self.store.add(
            "concept-a", "concept-b", "competes_with",
            evidence_ids=("evidence-a",), context_refs=("lab-1",),
        )
        self.assertEqual("competes_with", relation.relationship)
        self.assertEqual(("evidence-a",), relation.evidence_ids)
        self.assertEqual(("lab-1",), relation.context_refs)
        self.assertEqual(1, len(self.store.for_concept("concept-a")))
        self.assertEqual(1, len(self.store.for_concept("concept-b")))

    def test_relation_creation_is_idempotent(self) -> None:
        first = self.store.add("concept-a", "concept-b", "contradicts", evidence_ids=("evidence-a",))
        second = self.store.add("concept-a", "concept-b", "contradicts", evidence_ids=("evidence-a",))
        self.assertEqual(first, second)
        self.assertEqual(1, len(self.store.for_concept("concept-a")))

    def test_distinct_evidence_preserves_relation_history(self) -> None:
        self.store.add("concept-a", "concept-b", "contradicts", evidence_ids=("evidence-a",))
        self.store.add("concept-a", "concept-b", "contradicts", evidence_ids=("evidence-b",))
        self.assertEqual(2, len(self.store.for_concept("concept-a")))

    def test_does_not_delete_or_merge_competing_concepts(self) -> None:
        self.store.add("concept-a", "concept-b", "competes_with", evidence_ids=("evidence-a",))
        self.assertEqual("concept", self.memory.get("concept-a", record_access=False).kind)
        self.assertEqual("concept", self.memory.get("concept-b", record_access=False).kind)

    def test_rejects_non_concept_endpoint_and_missing_evidence(self) -> None:
        with self.assertRaises(ValueError):
            self.store.add("evidence-a", "concept-b", "supports", evidence_ids=("evidence-a",))
        with self.assertRaises(ValueError):
            self.store.add("concept-a", "concept-b", "supports", evidence_ids=("missing",))

    def test_rejects_self_relation_and_unknown_type(self) -> None:
        with self.assertRaises(ValueError):
            self.store.add("concept-a", "concept-a", "supports", evidence_ids=("evidence-a",))
        with self.assertRaises(ValueError):
            self.store.add("concept-a", "concept-b", "unknown", evidence_ids=("evidence-a",))


if __name__ == "__main__":
    unittest.main()
