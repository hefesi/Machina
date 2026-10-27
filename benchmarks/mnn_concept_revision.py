"""Synthetic benchmark for concept revision after new/contradictory evidence.

Run: python benchmarks/mnn_concept_revision.py
This validates review-state transitions, not semantic understanding.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from machina.fragment_memory import FragmentMemory  # noqa: E402
from machina.mnn_concept_review import MNNConceptReviewer  # noqa: E402
from machina.mnn_concepts import MNNConceptBuilder  # noqa: E402


def run() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        with FragmentMemory(Path(directory) / "revision.sqlite3") as memory:
            for identifier in ("obs-1", "obs-2"):
                memory.add(
                    f"Repeated observation {identifier}", source_uri=f"benchmark://{identifier}",
                    tags=["load-pattern"], confidence=0.8,
                    metadata={"polarity": "supports"}, fragment_id=identifier,
                )
            builder = MNNConceptBuilder(memory)
            original = builder.consolidate()[0]
            reviewer = MNNConceptReviewer(memory)
            before = next(item for item in reviewer.review() if item.concept.id == original.id)
            memory.add(
                "Counter observation", source_uri="benchmark://counter", tags=["load-pattern"],
                confidence=0.9, metadata={"polarity": "contradicts"}, fragment_id="obs-counter",
            )
            after_new_evidence = next(item for item in reviewer.review() if item.concept.id == original.id)
            reviewer.refresh()
            after_refresh = reviewer.review()
            return {
                "benchmark": "mnn_concept_revision",
                "original_state": before.state,
                "old_snapshot_after_new_evidence": after_new_evidence.state,
                "new_snapshot_states": [item.state for item in after_refresh if item.concept.id != original.id],
                "original_evidence_ids": list(original.metadata["evidence_ids"]),
                "old_snapshot_preserved": memory.get(original.id, record_access=False).id == original.id,
                "archive_records": memory.count(),
                "interpretation": "Synthetic state-transition check only; the reviewer uses explicit tags/polarity and does not infer natural-language semantics.",
            }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
