"""Tests for dynamic, non-destructive fragment memory."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory


class FragmentMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "fragments.sqlite3"
        self.memory = FragmentMemory(self.path)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def test_add_and_persist_fragment_with_provenance(self) -> None:
        fragment = self.memory.add(
            "A key design decision", source_uri="project://architecture",
            importance=0.9, confidence=0.95, tags=["architecture"],
            metadata={"decision": "keep archive"},
        )
        self.assertEqual("project://architecture", fragment.source_uri)
        self.assertEqual(1, self.memory.count())
        self.memory.close()
        self.memory = FragmentMemory(self.path)
        self.assertEqual("A key design decision", self.memory.archive()[0].content)

    def test_active_view_is_bounded_without_deleting_archive(self) -> None:
        self.memory.add("Important", source_uri="local://1", importance=0.9, fragment_id="important")
        self.memory.add("Routine", source_uri="local://2", importance=0.2, fragment_id="routine")
        self.assertEqual(["important"], [item.id for item in self.memory.active(limit=1)])
        self.assertEqual(2, self.memory.count())
        self.assertEqual(2, len(self.memory.archive()))

    def test_access_reinforces_recent_relevance(self) -> None:
        self.memory.add("Frequently used", source_uri="local://a", importance=0.4, fragment_id="used")
        self.memory.add("Rarely used", source_uri="local://b", importance=0.4, fragment_id="rare")
        for _ in range(12):
            self.memory.get("used")
        self.assertEqual("used", self.memory.active(limit=1)[0].id)

    def test_pin_protects_high_importance_memory(self) -> None:
        self.memory.add("Crucial fact", source_uri="local://critical", importance=0.1, pinned=True, fragment_id="critical")
        self.memory.add("Higher unpinned", source_uri="local://other", importance=0.8, fragment_id="other")
        self.assertEqual("critical", self.memory.active(limit=1)[0].id)

    def test_reinforce_changes_importance_and_can_pin(self) -> None:
        self.memory.add("Key fact", source_uri="local://fact", importance=0.3, fragment_id="fact")
        result = self.memory.reinforce("fact", importance_delta=0.5, confidence=0.9, pin=True)
        self.assertAlmostEqual(0.8, result.importance)
        self.assertEqual(0.9, result.confidence)
        self.assertTrue(result.pinned)

    def test_associations_are_bidirectional_and_do_not_merge(self) -> None:
        self.memory.add("Cause", source_uri="local://cause", fragment_id="cause")
        self.memory.add("Effect", source_uri="local://effect", fragment_id="effect")
        self.memory.link("cause", "effect")
        self.assertEqual(("effect",), self.memory.get("cause", record_access=False).related_ids)
        self.assertEqual(("cause",), self.memory.get("effect", record_access=False).related_ids)
        self.assertEqual(2, self.memory.count())

    def test_recall_finds_lexical_matches_by_query(self) -> None:
        self.memory.add("Circuito fechado permite corrente elétrica", source_uri="local://electricity", tags=["física"], fragment_id="electricity")
        self.memory.add("Receita de bolo de chocolate", source_uri="local://recipe", fragment_id="recipe")
        results = self.memory.recall("corrente elétrica circuito")
        self.assertEqual("electricity", results[0].id)
        self.assertNotIn("recipe", [item.id for item in results])

    def test_recall_can_include_associated_context(self) -> None:
        self.memory.add("Corrente elétrica", source_uri="local://current", fragment_id="current")
        self.memory.add("Lei de Ohm relaciona tensão, intensidade e resistência", source_uri="local://ohm", fragment_id="ohm")
        self.memory.link("current", "ohm")
        results = self.memory.recall("corrente elétrica", include_related=True)
        self.assertEqual({"current", "ohm"}, {item.id for item in results})

    def test_context_feedback_changes_only_contextual_ranking(self) -> None:
        relevant = self.memory.add(
            "alpha beta task memory",
            source_uri="local://context-relevant",
            importance=0.5,
            confidence=0.5,
            fragment_id="z-relevant",
        )
        distractor = self.memory.add(
            "alpha beta task memory",
            source_uri="local://context-distractor",
            importance=0.5,
            confidence=0.5,
            fragment_id="a-distractor",
        )
        baseline = self.memory.recall("alpha beta task", limit=2)
        self.assertEqual(["a-distractor", "z-relevant"], [item.id for item in baseline])

        scores, applied = self.memory.apply_context_feedback_batch(
            {"z-relevant": True, "a-distractor": False},
            context="maintenance",
            operation_id="maintenance-feedback-1",
            strength=0.4,
        )
        self.assertTrue(applied)
        self.assertEqual({"z-relevant": 0.9, "a-distractor": 0.1}, scores)
        contextual = self.memory.recall("alpha beta task", limit=2, context="maintenance")
        self.assertEqual(["z-relevant", "a-distractor"], [item.id for item in contextual])

        # Another task keeps its neutral contextual scores and original tie-break.
        other_context = self.memory.recall("alpha beta task", limit=2, context="research")
        self.assertEqual(["a-distractor", "z-relevant"], [item.id for item in other_context])
        self.assertEqual(0.5, self.memory.context_importance("z-relevant", "research"))
        self.assertAlmostEqual(relevant.importance, self.memory.get("z-relevant", record_access=False).importance)
        self.assertAlmostEqual(distractor.importance, self.memory.get("a-distractor", record_access=False).importance)

        replay_scores, replay_applied = self.memory.apply_context_feedback_batch(
            {"z-relevant": True, "a-distractor": False},
            context="MAINTENANCE",
            operation_id="maintenance-feedback-1",
            strength=0.4,
        )
        self.assertFalse(replay_applied)
        self.assertEqual(scores, replay_scores)
        self.assertAlmostEqual(0.9, self.memory.context_importance("z-relevant", "maintenance"))
        with self.assertRaisesRegex(ValueError, "different context feedback"):
            self.memory.apply_context_feedback_batch(
                {"z-relevant": False},
                context="maintenance",
                operation_id="maintenance-feedback-1",
                strength=0.4,
            )

    def test_recall_validates_query_and_limit(self) -> None:
        with self.assertRaises(ValueError):
            self.memory.recall("   ")
        with self.assertRaises(ValueError):
            self.memory.recall("memória", limit=0)

    def test_invalid_values_and_missing_ids_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.memory.add("", source_uri="local://bad")
        with self.assertRaises(ValueError):
            self.memory.add("x", source_uri="local://bad", importance=1.2)
        with self.assertRaises(ValueError):
            self.memory.active(limit=0)
        with self.assertRaises(KeyError):
            self.memory.get("missing")


if __name__ == "__main__":
    unittest.main()
