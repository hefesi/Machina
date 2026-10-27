"""Tests for short-/long-term memory consolidation projections."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_memory_consolidation import MNNMemoryConsolidator


class MNNMemoryConsolidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "memory.sqlite3"
        self.memory = FragmentMemory(self.path)
        self.consolidator = MNNMemoryConsolidator(self.memory)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def test_important_old_record_remains_long_term(self) -> None:
        important = self.memory.add(
            "Critical safety invariant", source_uri="test://safety",
            importance=0.95, confidence=0.9, fragment_id="safety",
        )
        now = datetime.fromisoformat(important.last_accessed_at) + timedelta(days=365)
        results = self.consolidator.consolidate(now=now)
        by_id = {item.fragment.id: item for item in results}
        self.assertEqual("long_term", by_id["safety"].tier)
        self.assertIn("high_importance", by_id["safety"].reasons)

    def test_repeated_access_can_consolidate_a_moderate_record(self) -> None:
        fragment = self.memory.add(
            "Recurring workflow preference", source_uri="test://preference",
            importance=0.4, confidence=0.4, fragment_id="recurring",
        )
        for _ in range(12):
            self.memory.get(fragment.id)
        result = {item.fragment.id: item for item in self.consolidator.consolidate()}[fragment.id]
        self.assertEqual("long_term", result.tier)
        self.assertIn("repeated_access", result.reasons)

    def test_low_priority_is_short_term_not_deleted(self) -> None:
        self.memory.add(
            "One-off incidental detail", source_uri="test://incidental",
            importance=0.1, confidence=0.1, fragment_id="incidental",
        )
        result = self.consolidator.consolidate()
        self.assertEqual("short_term", result[0].tier)
        self.assertEqual(1, self.memory.count())
        self.assertEqual("incidental", self.memory.archive()[0].id)

    def test_pinned_record_is_long_term_and_ranked_first(self) -> None:
        self.memory.add("Routine note", source_uri="test://routine", importance=0.4, fragment_id="routine")
        self.memory.add("Pinned rule", source_uri="test://pinned", importance=0.1, pinned=True, fragment_id="pinned")
        result = self.consolidator.consolidate()
        self.assertEqual("pinned", result[0].fragment.id)
        self.assertEqual("long_term", result[0].tier)
        self.assertIn("pinned", result[0].reasons)

    def test_snapshot_restore_preserves_policy_and_archive(self) -> None:
        self.memory.add("Durable note", source_uri="test://durable", importance=0.9, fragment_id="durable")
        restored = MNNMemoryConsolidator.from_snapshot(self.consolidator.snapshot(), self.memory)
        self.assertEqual(self.consolidator.snapshot(), restored.snapshot())
        self.assertEqual([x.fragment.id for x in self.consolidator.consolidate()], [x.fragment.id for x in restored.consolidate()])

    def test_limit_only_bounds_projection(self) -> None:
        for i in range(4):
            self.memory.add(f"Record {i}", source_uri=f"test://{i}", importance=i / 4, fragment_id=f"r{i}")
        self.assertEqual(2, len(self.consolidator.consolidate(limit=2)))
        self.assertEqual(4, self.memory.count())

    def test_invalid_configuration_and_naive_clock_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MNNMemoryConsolidator(self.memory, importance_weight=0.5)
        with self.assertRaises(ValueError):
            self.consolidator.consolidate(now=datetime(2026, 1, 1))
        with self.assertRaises(ValueError):
            self.consolidator.consolidate(limit=0)


if __name__ == "__main__":
    unittest.main()
