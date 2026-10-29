"""Synthetic demonstration of evidence-grounded MNN concept formation.

Run from repository root: python benchmarks/mnn_concepts.py
This checks traceability and explicit conflict detection, not semantic reasoning.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from machina.fragment_memory import FragmentMemory  # noqa: E402
from machina.mnn_concepts import MNNConceptBuilder  # noqa: E402


def run() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        with FragmentMemory(Path(directory) / "concepts.sqlite3") as memory:
            memory.add(
                "Repeated observation: the machine overheats under heavy load",
                source_uri="benchmark://observation/1", tags=["heavy-load", "temperature"],
                confidence=0.85, metadata={"polarity": "supports"}, fragment_id="obs-1",
            )
            memory.add(
                "Repeated observation: the machine overheats under sustained load",
                source_uri="benchmark://observation/2", tags=["heavy-load", "temperature"],
                confidence=0.75, metadata={"polarity": "supports"}, fragment_id="obs-2",
            )
            memory.add(
                "Counter-observation: temperature remained stable in a controlled run",
                source_uri="benchmark://observation/3", tags=["temperature", "controlled-run"],
                confidence=0.8, metadata={"polarity": "contradicts"}, fragment_id="obs-3",
            )
            builder = MNNConceptBuilder(memory, min_support=2)
            hypotheses = builder.discover()
            concepts = builder.consolidate()
            return {
                "benchmark": "mnn_evidence_concepts",
                "source_records": 3,
                "hypotheses_discovered": len(hypotheses),
                "concept_records_materialized": len(concepts),
                "hypotheses": [
                    {"key": item.key, "status": item.status, "support_count": item.support_count,
                     "confidence_heuristic": round(item.confidence, 4),
                     "evidence_ids": list(item.evidence_ids),
                     "supporting_ids": list(item.supporting_ids),
                     "contradicting_ids": list(item.contradicting_ids)}
                    for item in hypotheses
                ],
                "archive_records_after": memory.count(),
                "interpretation": "Synthetic tag co-occurrence and explicit polarity check only; no free-form semantic understanding is claimed.",
            }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
