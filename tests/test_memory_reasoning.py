"""Tests for explainable context expansion and structured claim conflicts."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.memory_reasoning import find_structured_conflicts, retrieve_context


class MemoryReasoningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp_dir.name) / "memory.sqlite3")

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def test_explicit_alias_recovers_fragment_missed_by_lexical_query(self) -> None:
        self.memory.add(
            "A closed circuit allows electric current to flow.",
            source_uri="lab://electricity",
            tags=["physics"],
            fragment_id="electric-current",
        )
        self.assertEqual([], self.memory.recall("electron movement"))
        results = retrieve_context(
            self.memory, "electron movement",
            aliases={"electron": ["electric current", "closed circuit"]},
        )
        self.assertIn("electric-current", [item.id for item in results])

    def test_associated_context_is_preserved_and_results_are_deduplicated(self) -> None:
        self.memory.add("Electric current", source_uri="lab://current", fragment_id="current")
        self.memory.add("Ohm law relates voltage and resistance", source_uri="lab://ohm", fragment_id="ohm")
        self.memory.link("current", "ohm")
        results = retrieve_context(self.memory, "electric current", aliases={"current": ["current"]})
        ids = [item.id for item in results]
        self.assertEqual(2, len(ids))
        self.assertEqual({"current", "ohm"}, set(ids))

    def test_conflict_detection_returns_both_evidence_sources(self) -> None:
        first = self.memory.add(
            "The experiment says the valve is open.",
            source_uri="lab://trial-1",
            fragment_id="claim-open",
            metadata={"claim": {"subject": "valve A", "predicate": "state", "value": "open"}},
        )
        second = self.memory.add(
            "A later observation says the valve is closed.",
            source_uri="lab://trial-2",
            fragment_id="claim-closed",
            metadata={"claim": {"subject": "Valve A", "predicate": "State", "value": "closed"}},
        )
        conflicts = find_structured_conflicts([first, second])
        self.assertEqual(1, len(conflicts))
        conflict = conflicts[0]
        self.assertEqual(("claim-open", "claim-closed"), (
            conflict.first_fragment_id, conflict.second_fragment_id
        ))
        self.assertEqual(("lab://trial-1", "lab://trial-2"), (
            conflict.first_source_uri, conflict.second_source_uri
        ))

    def test_equal_claim_values_are_not_a_conflict(self) -> None:
        first = self.memory.add(
            "The sensor reads 12.", source_uri="lab://a",
            metadata={"claim": {"subject": "sensor", "predicate": "reading", "value": "12"}},
        )
        second = self.memory.add(
            "The sensor reads twelve.", source_uri="lab://b",
            metadata={"claim": {"subject": "sensor", "predicate": "reading", "value": "12"}},
        )
        self.assertEqual([], find_structured_conflicts([first, second]))

    def test_unstructured_text_does_not_trigger_contradiction_guess(self) -> None:
        first = self.memory.add("The sky appears blue.", source_uri="lab://a")
        second = self.memory.add("The sky appears grey.", source_uri="lab://b")
        self.assertEqual([], find_structured_conflicts([first, second]))

    def test_query_and_limit_validation(self) -> None:
        with self.assertRaises(ValueError):
            retrieve_context(self.memory, " ")
        with self.assertRaises(ValueError):
            retrieve_context(self.memory, "memory", limit=0)


if __name__ == "__main__":
    unittest.main()
