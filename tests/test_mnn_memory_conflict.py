import tempfile
import unittest
from pathlib import Path

from machina import FragmentMemory
from machina.mnn_memory_conflict import MNNMemoryConflictReviewer


class MNNMemoryConflictReviewerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp.name) / "memory.sqlite3")
        self.memory.add(
            "The system uses rule A under condition X.",
            source_uri="test://prior",
            fragment_id="memory-1",
        )
        self.reviewer = MNNMemoryConflictReviewer()

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def review(self, relationship):
        return self.reviewer.review(
            self.memory,
            "memory-1",
            "New observation indicates rule B under condition X.",
            relationship=relationship,
            evidence_id="observation:2",
            context_refs=("episode:2", "episode:1"),
        )

    def test_contradiction_requests_review_and_preserves_memory(self):
        result = self.review("contradicts")
        self.assertEqual("needs_review", result.recommendation)
        self.assertEqual(
            "The system uses rule A under condition X.",
            self.memory.get("memory-1", record_access=False).content,
        )
        self.assertEqual(("episode:1", "episode:2"), result.context_refs)
        self.assertEqual(0, len(self.memory.revision_history("memory-1")))

    def test_support_does_not_overwrite_prior_record(self):
        result = self.review("supports")
        self.assertEqual("corroborate_without_rewrite", result.recommendation)
        self.assertEqual(
            "The system uses rule A under condition X.",
            self.memory.get("memory-1", record_access=False).content,
        )

    def test_contextual_information_preserves_both(self):
        self.assertEqual("preserve_both", self.review("contextualizes").recommendation)

    def test_uncertain_relationship_defers(self):
        self.assertEqual("defer", self.review("uncertain").recommendation)

    def test_unrelated_information_is_not_a_conflict(self):
        self.assertEqual("no_conflict", self.review("unrelated").recommendation)

    def test_invalid_relationship_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "relationship must be one of"):
            self.review("probably-contradictory")


if __name__ == "__main__":
    unittest.main()
