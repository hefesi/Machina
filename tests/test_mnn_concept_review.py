"""Tests for concept freshness review and non-destructive revision."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_concept_review import MNNConceptReviewer
from machina.mnn_concepts import MNNConceptBuilder


class MNNConceptReviewerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp_dir.name) / "review.sqlite3")
        self.builder = MNNConceptBuilder(self.memory, min_support=2)
        self.reviewer = MNNConceptReviewer(self.memory, min_support=2)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def add(self, identifier: str, polarity: str = "supports") -> None:
        self.memory.add(
            f"Observation {identifier}", source_uri=f"test://{identifier}",
            tags=["load-pattern"], confidence=0.8,
            metadata={"polarity": polarity}, fragment_id=identifier,
        )

    def test_matching_evidence_is_current(self) -> None:
        self.add("a")
        self.add("b")
        concept = self.builder.consolidate()[0]
        review = next(item for item in self.reviewer.review() if item.concept.id == concept.id)
        self.assertEqual("current", review.state)
        self.assertEqual((), review.added_evidence_ids)
        self.assertEqual((), review.missing_evidence_ids)

    def test_new_evidence_marks_old_snapshot_stale_and_refresh_keeps_history(self) -> None:
        self.add("a")
        self.add("b")
        old_concept = self.builder.consolidate()[0]
        old_count = self.memory.count()
        self.add("c")
        review = next(item for item in self.reviewer.review() if item.concept.id == old_concept.id)
        self.assertEqual("stale", review.state)
        self.assertEqual(("c",), review.added_evidence_ids)
        new_concepts = self.reviewer.refresh()
        self.assertTrue(any(item.id != old_concept.id for item in new_concepts))
        self.assertEqual(old_count + 2, self.memory.count())  # new evidence + refreshed concept
        self.assertEqual(old_concept.id, self.memory.get(old_concept.id, record_access=False).id)

    def test_new_contradiction_marks_current_concept_conflicted(self) -> None:
        self.add("a")
        self.add("b")
        self.builder.consolidate()
        self.add("counter", "contradicts")
        self.reviewer.refresh()
        reviews = self.reviewer.review()
        self.assertTrue(any(item.state == "conflicted" for item in reviews))

    def test_review_log_is_idempotent_for_same_review_state(self) -> None:
        self.add("a")
        self.add("b")
        self.builder.consolidate()
        first = self.reviewer.persist_review_log()
        count_after_first = self.memory.count()
        second = self.reviewer.persist_review_log()
        self.assertEqual([item.id for item in first], [item.id for item in second])
        self.assertEqual(count_after_first, self.memory.count())
        self.assertEqual("concept_review", first[0].kind)

    def test_invalid_provenance_is_unverified(self) -> None:
        self.memory.add(
            "Manually created concept without provenance", kind="concept",
            source_uri="test://manual", metadata={}, fragment_id="manual-concept",
        )
        review = next(item for item in self.reviewer.review() if item.concept.id == "manual-concept")
        self.assertEqual("unverified", review.state)


if __name__ == "__main__":
    unittest.main()
