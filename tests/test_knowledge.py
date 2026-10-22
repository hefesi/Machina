"""Tests for Machina's persistent knowledge store."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.knowledge import DuplicateKnowledgeError, KnowledgeStore


class KnowledgeStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "knowledge.sqlite3"
        self.store = KnowledgeStore(self.path)

    def tearDown(self) -> None:
        self.store.close()
        self.temp_dir.cleanup()

    def test_add_and_retrieve_document_preserves_provenance(self) -> None:
        document = self.store.add_document(
            title="MNN plasticity",
            content="Plasticity changes connection weights after an evaluated outcome.",
            source_uri="https://example.test/mnn",
            source_type="web",
            confidence=0.8,
            metadata={"author": "research note", "tags": ["MNN", "learning"]},
            document_id="mnn-plasticity",
        )
        loaded = self.store.get_document("mnn-plasticity")
        self.assertEqual(document, loaded)
        self.assertEqual("https://example.test/mnn", loaded.source_uri)
        self.assertEqual(0.8, loaded.confidence)
        self.assertEqual(["MNN", "learning"], loaded.metadata["tags"])

    def test_search_ranks_title_match_and_reports_matched_terms(self) -> None:
        self.store.add_document(
            title="Memory systems",
            content="A persistent store records facts and sources.",
            source_uri="local://memory",
            document_id="memory",
        )
        self.store.add_document(
            title="MNN plasticity",
            content="MNN plasticity adjusts neural connection weights after feedback.",
            source_uri="local://mnn",
            document_id="plasticity",
        )
        hits = self.store.search("MNN plasticity", limit=2)
        self.assertEqual("plasticity", hits[0].document.id)
        self.assertEqual(("mnn", "plasticity"), hits[0].matched_terms)
        self.assertGreater(hits[0].score, hits[1].score)

    def test_search_is_deterministic_for_ties(self) -> None:
        for identifier in ("b", "a"):
            self.store.add_document(
                title="Shared topic",
                content="shared topic evidence",
                source_uri=f"local://{identifier}",
                document_id=identifier,
            )
        self.assertEqual(
            [hit.document.id for hit in self.store.search("shared topic")],
            ["a", "b"],
        )

    def test_duplicate_id_does_not_overwrite_existing_document(self) -> None:
        self.store.add_document(
            title="Original", content="Original content",
            source_uri="local://original", document_id="same",
        )
        with self.assertRaises(DuplicateKnowledgeError):
            self.store.add_document(
                title="Replacement", content="Replacement content",
                source_uri="local://replacement", document_id="same",
            )
        self.assertEqual("Original", self.store.get_document("same").title)

    def test_invalid_inputs_are_rejected(self) -> None:
        for confidence in (-0.1, 1.1, float("nan"), float("inf")):
            with self.subTest(confidence=confidence):
                with self.assertRaises(ValueError):
                    self.store.add_document(
                        title="Title", content="Content",
                        source_uri="local://source", confidence=confidence,
                    )
        with self.assertRaises(ValueError):
            self.store.add_document(title="", content="x", source_uri="local://source")
        with self.assertRaises(ValueError):
            self.store.search("   ")
        with self.assertRaises(ValueError):
            self.store.search("anything", limit=0)

    def test_metadata_must_be_json_serializable_and_finite(self) -> None:
        with self.assertRaises(ValueError):
            self.store.add_document(
                title="Title", content="Content", source_uri="local://source",
                metadata={"invalid": object()},
            )
        with self.assertRaises(ValueError):
            self.store.add_document(
                title="Title", content="Content", source_uri="local://source",
                metadata={"invalid": float("nan")},
            )

    def test_persistence_survives_close_and_reopen(self) -> None:
        self.store.add_document(
            title="Persisted fact", content="The fact remains after restart.",
            source_uri="local://persist", document_id="persisted",
        )
        self.store.close()
        self.store = KnowledgeStore(self.path)
        self.assertEqual("persisted", self.store.search("persisted fact")[0].document.id)
        self.assertEqual(1, self.store.count())

    def test_unknown_document_and_closed_store_fail_clearly(self) -> None:
        with self.assertRaises(KeyError):
            self.store.get_document("missing")
        self.store.close()
        with self.assertRaises(RuntimeError):
            self.store.count()


if __name__ == "__main__":
    unittest.main()
