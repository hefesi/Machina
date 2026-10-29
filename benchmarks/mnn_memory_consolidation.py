"""Compare recency-only ranking with consolidation-aware retention.

Run from the repository root: python benchmarks/mnn_memory_consolidation.py
This synthetic benchmark checks whether recurring/high-importance signals stay
available after a simulated year; it is not evidence of general cognition.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from machina.fragment_memory import FragmentMemory  # noqa: E402
from machina.mnn_memory_consolidation import MNNMemoryConsolidator  # noqa: E402


def run() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        memory = FragmentMemory(Path(directory) / "benchmark.sqlite3")
        try:
            important = memory.add(
                "Critical safety rule", source_uri="benchmark://safety",
                importance=0.98, confidence=0.95, fragment_id="critical-safety",
            )
            recurring = memory.add(
                "Repeated workflow preference", source_uri="benchmark://preference",
                importance=0.45, confidence=0.6, fragment_id="recurring-preference",
            )
            incidental = memory.add(
                "One-time incidental observation", source_uri="benchmark://incidental",
                importance=0.15, confidence=0.3, fragment_id="incidental-note",
            )
            for _ in range(12):
                memory.get(recurring.id)
            now = datetime.fromisoformat(important.last_accessed_at) + timedelta(days=365)
            ranked = MNNMemoryConsolidator(memory).consolidate(now=now)
            by_id = {item.fragment.id: item for item in ranked}
            return {
                "benchmark": "mnn_memory_consolidation",
                "scenario": "year-old archive with one critical, one repeatedly accessed, and one incidental record",
                "archive_records_before": 3,
                "archive_records_after": memory.count(),
                "critical_retained_long_term": by_id["critical-safety"].tier == "long_term",
                "recurring_retained_long_term": by_id["recurring-preference"].tier == "long_term",
                "incidental_tier": by_id["incidental-note"].tier,
                "ranked_records": [
                    {"id": item.fragment.id, "tier": item.tier, "score": round(item.score, 4), "reasons": list(item.reasons)}
                    for item in ranked
                ],
                "interpretation": "Synthetic mechanism check only; ranking and tiers are heuristics, not measured human memory or general intelligence.",
            }
        finally:
            memory.close()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
