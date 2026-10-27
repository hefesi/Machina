"""Small deterministic smoke benchmark for conservative concept guidance.

Run with: python benchmarks/mnn_concept_guidance.py
This reports policy outcomes, not a claim of general decision-quality gains.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_concept_advisor import MNNConceptAdvisor
from machina.mnn_concepts import MNNConceptBuilder


def add(memory: FragmentMemory, identifier: str, tag: str, polarity: str = "supports") -> None:
    memory.add(
        f"Synthetic evidence {identifier}", kind="fact",
        source_uri=f"benchmark://{identifier}", tags=(tag,), confidence=0.9,
        metadata={"polarity": polarity}, fragment_id=identifier,
    )


def run() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        memory = FragmentMemory(Path(directory) / "guidance.sqlite3")
        try:
            add(memory, "stable-1", "stable-context")
            add(memory, "stable-2", "stable-context")
            add(memory, "risk-1", "risk-context")
            add(memory, "risk-2", "risk-context")
            builder = MNNConceptBuilder(memory, min_support=2)
            builder.consolidate()
            advisor = MNNConceptAdvisor(memory, {
                "stable-context": "continue",
                "risk-context": "pause",
            })
            results = {
                "supported_single_match": advisor.recommend(["stable-context"]),
                "ambiguous_multi_match": advisor.recommend(["stable-context", "risk-context"]),
                "unknown_context": advisor.recommend(["unknown-context"]),
            }
            add(memory, "stable-counter", "stable-context", "contradicts")
            builder.consolidate()
            results["explicit_conflict"] = advisor.recommend(["stable-context"])
            return {
                "benchmark": "mnn-concept-guidance-smoke",
                "note": "Synthetic deterministic contract check; not evidence of generalization.",
                "scenarios": {
                    name: {
                        "status": value["status"],
                        "reason": value["reason"],
                    }
                    for name, value in results.items()
                },
            }
        finally:
            memory.close()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
