"""Evaluate priority decay separately from archive deletion and recall failure.

The benchmark ages one record deterministically in SQLite rather than sleeping.
It then checks the active ranked view, full archive, lexical recall, direct
lookup, and explicit reinforcement. This is a storage/retrieval experiment,
not a semantic-memory or consciousness benchmark.
"""
from __future__ import annotations

import json
import math
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from machina.fragment_memory import FragmentMemory


def run_benchmark(storage_path: str | Path | None = None) -> dict[str, Any]:
    """Return reproducible evidence distinguishing decay, omission, and deletion."""
    temporary = None
    if storage_path is None:
        temporary = tempfile.TemporaryDirectory()
        storage_path = Path(temporary.name) / "fragments.sqlite3"

    memory = FragmentMemory(storage_path, decay_per_day=0.8, usage_reinforcement=0.0)
    try:
        aged = memory.add(
            "Important project rule: preserve the archive during prioritization.",
            source_uri="project://memory/rule",
            importance=0.8,
            confidence=0.95,
            tags=["archive", "preservation"],
            fragment_id="aged-important-rule",
        )
        recent = memory.add(
            "Recent note about a routine sensor reading.",
            source_uri="project://memory/recent",
            importance=0.7,
            confidence=0.9,
            tags=["sensor"],
            fragment_id="recent-routine-note",
        )
        protected = memory.add(
            "Critical recovery key: retain this high-value information.",
            source_uri="project://memory/protected",
            importance=0.2,
            confidence=1.0,
            pinned=True,
            tags=["critical"],
            fragment_id="pinned-critical",
        )

        # Simulate 30 days without access deterministically. This touches only
        # the fixture's timestamp, not the memory API or priority itself.
        old_timestamp = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        memory._db.execute(
            "UPDATE memory_fragments SET last_accessed_at = ? WHERE id = ?",
            (old_timestamp, aged.id),
        )
        memory._db.commit()

        active = memory.active(limit=1)
        active_ids = [fragment.id for fragment in active]
        all_ranked = {fragment.id: fragment for fragment in memory.active(limit=3)}
        archive_before = memory.archive()
        archive_ids_before = [fragment.id for fragment in archive_before]
        aged_priority = all_ranked["aged-important-rule"].priority
        recent_priority = all_ranked["recent-routine-note"].priority

        # Deliberately unrelated query: lexical recall should fail while the
        # stored record remains directly addressable and present in archive.
        lexical_miss = memory.recall("quasar penguin", include_related=False)
        direct_lookup = memory.get("aged-important-rule", record_access=False)

        reinforced = memory.reinforce(
            "aged-important-rule", importance_delta=0.15, pin=True
        )
        active_after_reinforcement = memory.active(limit=1)
        archive_after = memory.archive()
        archive_ids_after = [fragment.id for fragment in archive_after]

        expected_decayed_priority = 0.8 * math.exp(-0.8 * 30)
        passed = (
            "recent-routine-note" in active_ids
            and "aged-important-rule" in archive_ids_before
            and len(archive_ids_before) == 3
            and aged_priority < recent_priority
            and abs(aged_priority - expected_decayed_priority) < 1e-9
            and lexical_miss == []
            and direct_lookup.content == aged.content
            and reinforced.pinned
            and abs(reinforced.importance - 0.95) < 1e-12
            and active_after_reinforcement[0].id == "aged-important-rule"
            and archive_ids_after == archive_ids_before
            and memory.count() == 3
            and protected.pinned
            and recent.id in archive_ids_after
        )
        return {
            "benchmark": "fragment_memory_decay_vs_retrieval",
            "version": 1,
            "parameters": {
                "decay_per_day": 0.8,
                "simulated_age_days": 30,
                "active_limit": 1,
                "usage_reinforcement": 0.0,
            },
            "active_view_before_reinforcement": {
                "limit": 1,
                "ids": active_ids,
                "aged_rule_priority": aged_priority,
                "recent_note_priority": recent_priority,
                "aged_rule_in_active_view": "aged-important-rule" in active_ids,
            },
            "archive_before_reinforcement": {
                "count": len(archive_ids_before),
                "ids": archive_ids_before,
                "aged_rule_present": "aged-important-rule" in archive_ids_before,
            },
            "lexical_retrieval_probe": {
                "query": "quasar penguin",
                "result_count": len(lexical_miss),
                "direct_lookup_succeeded": direct_lookup.content == aged.content,
                "interpretation": (
                    "The lexical query misses, but direct lookup and archive "
                    "show that the record is stored. This is evidence of a "
                    "retrieval miss in this fixture, not deletion."
                ),
            },
            "reinforcement_probe": {
                "importance_after_reinforcement": reinforced.importance,
                "pinned": reinforced.pinned,
                "active_top_id": active_after_reinforcement[0].id,
            },
            "archive_after_reinforcement": {
                "count": len(archive_ids_after),
                "ids_unchanged": archive_ids_after == archive_ids_before,
            },
            "passed": passed,
            "interpretation": (
                "Priority decay and bounded active views do not delete records. "
                "A lexical query can miss a stored fragment, while direct lookup "
                "and archive still find it. Explicit reinforcement can restore "
                "the fragment to the top active position. This does not establish "
                "semantic understanding or human-like memory."
            ),
        }
    finally:
        memory.close()
        if temporary is not None:
            temporary.cleanup()


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
