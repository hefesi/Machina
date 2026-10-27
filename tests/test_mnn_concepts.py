"""Tests for evidence-grounded concept discovery and provenance."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_concepts import MNNConceptBuilder


class MNNConceptBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp_dir.name) / "concepts.sqlite3")
        self.builder = MNNConceptBuilder(self.memory, min_support=2)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def add_evidence(self, identifier: str, polarity: str = "supports", *, confidence: float = 0.8) -> None:
        self.memory.add(
            f"Observation {identifier}",
            source_uri=f"test://{identifier}",
            confidence=confidence,
            tags=["temperature", "experiment"],
            metadata={"polarity": polarity},
            fragment_id=identifier,
        )

    def test_recurring_tag_yields_supported_hypothesis(self) -> None:
        self.add_evidence("e1")
        self.add_evidence("e2")
        hypotheses = self.builder.discover()
        temperature = next(item for item in hypotheses if item.key == "temperature")
        self.assertEqual("supported", temperature.status)
        self.assertEqual(("e1", "e2"), temperature.evidence_ids)
        self.assertGreater(temperature.confidence, 0.0)
        self.assertLess(temperature.confidence, 0.8)

    def test_explicit_opposing_polarities_mark_conflict(self) -> None:
        self.add_evidence("positive", "supports")
        self.add_evidence("negative", "contradicts")
        hypothesis = next(item for item in self.builder.discover() if item.key == "temperature")
        self.assertEqual("conflicted", hypothesis.status)
        self.assertEqual(("positive",), hypothesis.supporting_ids)
        self.assertEqual(("negative",), hypothesis.contradicting_ids)

    def test_unknown_polarity_is_not_assumed_to_support(self) -> None:
        self.add_evidence("unknown-a", "unknown")
        self.add_evidence("unknown-b", "unknown")
        hypothesis = next(item for item in self.builder.discover() if item.key == "temperature")
        self.assertEqual("insufficient", hypothesis.status)
        self.assertEqual(2, len(hypothesis.unknown_polarity_ids))

    def test_materialized_concept_keeps_evidence_provenance(self) -> None:
        self.add_evidence("source-a")
        self.add_evidence("source-b")
        hypothesis = next(item for item in self.builder.discover() if item.key == "temperature")
        before = self.memory.count()
        concept = self.builder.materialize(hypothesis)
        self.assertEqual("concept", concept.kind)
        self.assertEqual(["source-a", "source-b"], concept.metadata["evidence_ids"])
        self.assertEqual(("source-a", "source-b"), concept.related_ids)
        self.assertEqual(before + 1, self.memory.count())

    def test_materialization_is_idempotent_for_same_evidence(self) -> None:
        self.add_evidence("source-a")
        self.add_evidence("source-b")
        hypothesis = next(item for item in self.builder.discover() if item.key == "temperature")
        first = self.builder.materialize(hypothesis)
        second = self.builder.materialize(hypothesis)
        self.assertEqual(first.id, second.id)
        self.assertEqual(3, self.memory.count())

    def test_derived_concepts_are_not_used_as_source_evidence(self) -> None:
        self.add_evidence("source-a")
        self.add_evidence("source-b")
        self.builder.consolidate()
        hypotheses = self.builder.discover()
        temperature = next(item for item in hypotheses if item.key == "temperature")
        self.assertEqual(2, temperature.support_count)
        self.assertNotIn("concept", temperature.evidence_ids)

    def test_minimum_support_and_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            MNNConceptBuilder(self.memory, min_support=1)
        self.add_evidence("only-one")
        self.assertEqual([], self.builder.discover())
        with self.assertRaises(ValueError):
            self.builder.discover(include_kinds=())


if __name__ == "__main__":
    unittest.main()
