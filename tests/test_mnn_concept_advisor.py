"""Tests for conservative action guidance from reviewed concepts."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_concept_advisor import MNNConceptAdvisor
from machina.mnn_concepts import MNNConceptBuilder


class MNNConceptAdvisorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp_dir.name) / "advisor.sqlite3")
        self.builder = MNNConceptBuilder(self.memory, min_support=2)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def add(self, identifier: str, tag: str = "stable-context", polarity: str = "supports") -> None:
        self.memory.add(
            f"Evidence {identifier}", kind="fact", source_uri=f"test://{identifier}",
            tags=(tag,), confidence=0.9, metadata={"polarity": polarity},
            fragment_id=identifier,
        )

    def advisor(self, mapping=None) -> MNNConceptAdvisor:
        return MNNConceptAdvisor(
            self.memory, mapping or {"stable-context": "continue"},
            min_support=2,
        )

    def test_supported_current_concept_recommends_explicitly_mapped_action(self) -> None:
        self.add("e1")
        self.add("e2")
        concept = self.builder.consolidate()[0]
        result = self.advisor().recommend(["stable-context"])
        self.assertEqual("recommended", result["status"])
        recommendation = result["recommendation"]
        self.assertEqual("continue", recommendation["action"])
        self.assertEqual(concept.id, recommendation["concepts"][0]["concept_id"])
        self.assertEqual({"e1", "e2"}, set(recommendation["concepts"][0]["evidence_ids"]))

    def test_unknown_tag_abstains(self) -> None:
        result = self.advisor().recommend(["unmapped-context"])
        self.assertEqual("abstained", result["status"])
        self.assertEqual("no_configured_concept_match", result["reason"])

    def test_stale_concept_abstains_until_refreshed(self) -> None:
        self.add("e1")
        self.add("e2")
        self.builder.consolidate()
        self.add("e3")
        result = self.advisor().recommend(["stable-context"])
        self.assertEqual("abstained", result["status"])
        self.assertIn("stale_or_unverified_concept", result["blocked_concepts"].values())

    def test_conflicted_evidence_blocks_recommendation(self) -> None:
        self.add("e1")
        self.add("e2")
        self.builder.consolidate()
        self.add("counter", polarity="contradicts")
        self.builder.consolidate()
        result = self.advisor().recommend(["stable-context"])
        self.assertEqual("abstained", result["status"])
        self.assertIn("conflicted_evidence", result["blocked_concepts"].values())

    def test_ambiguous_actions_abstain(self) -> None:
        self.add("e1", "stable-context")
        self.add("e2", "stable-context")
        self.add("e3", "low-risk")
        self.add("e4", "low-risk")
        self.builder.consolidate()
        result = self.advisor({
            "stable-context": "continue",
            "low-risk": "pause",
        }).recommend(["stable-context", "low-risk"])
        self.assertEqual("abstained", result["status"])
        self.assertEqual("ambiguous_action_mapping", result["reason"])

    def test_invalid_context_tags_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.advisor().recommend("stable-context")
        with self.assertRaises(ValueError):
            self.advisor().recommend([""])

    def test_invalid_mapping_and_threshold_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MNNConceptAdvisor(self.memory, {})
        with self.assertRaises(ValueError):
            MNNConceptAdvisor(self.memory, {"stable-context": "continue"}, min_confidence=2)


if __name__ == "__main__":
    unittest.main()
