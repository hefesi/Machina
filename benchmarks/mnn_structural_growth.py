"""Demonstrate learning a new path through bounded structural growth.

During training, the cue and the response are both active (teacher forcing).
The growth policy adds a weighted cue -> response edge. During evaluation only
the cue is provided, so the response must be produced through the new edge.
This is a narrow structural-association experiment, not evidence of general
autonomy or intelligence.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any

from machina.mnn import MNN, Unit
from machina.mnn_checkpoint import MNNCheckpointStore
from machina.mnn_structure import ActivityGrowthPolicy


def make_network() -> MNN:
    network = MNN(weight_limit=2.0)
    network.add_unit(Unit("cue", activation="identity"))
    network.add_unit(Unit("response", activation="identity"))
    return network


def _response_to_cue(network: MNN) -> float:
    network.reset_states()
    network.step({"cue": 1.0})
    return network.step({"cue": 1.0})["response"]


def run_benchmark(
    *,
    checkpoint_path: str | Path | None = None,
    initial_weight: float = 0.75,
) -> dict[str, Any]:
    if isinstance(initial_weight, bool):
        raise ValueError("initial_weight must be a finite positive number")
    try:
        weight = float(initial_weight)
    except (TypeError, ValueError) as error:
        raise ValueError("initial_weight must be a finite positive number") from error
    if not math.isfinite(weight) or weight <= 0:
        raise ValueError("initial_weight must be a finite positive number")

    network = make_network()
    baseline = _response_to_cue(MNN.from_snapshot(network.snapshot()))

    network.reset_states()
    network.step({"cue": 1.0, "response": 1.0})
    policy = ActivityGrowthPolicy(
        max_new_connections=1,
        initial_weight=weight,
        min_activity=0.1,
        allowed_sources={"cue"},
        allowed_targets={"response"},
    )
    grown = policy.grow(network)
    trained = _response_to_cue(MNN.from_snapshot(network.snapshot()))
    grown_edges = [
        {
            "id": item.connection.id,
            "source": item.connection.source,
            "target": item.connection.target,
            "weight": item.connection.weight,
            "score": item.score,
        }
        for item in grown
    ]
    trained_weights = {
        edge_id: edge.weight for edge_id, edge in network.connections.items()
    }

    if checkpoint_path is None:
        with tempfile.TemporaryDirectory() as directory:
            store = MNNCheckpointStore(Path(directory) / "structural-growth.json")
            store.save(network)
            restored_network = store.load()
    else:
        store = MNNCheckpointStore(checkpoint_path)
        store.save(network)
        restored_network = store.load()

    restored = _response_to_cue(restored_network)
    restored_weights = {
        edge_id: edge.weight for edge_id, edge in restored_network.connections.items()
    }
    passed = (
        baseline == 0.0
        and trained == weight
        and restored == trained
        and len(grown_edges) == 1
        and grown_edges[0]["source"] == "cue"
        and grown_edges[0]["target"] == "response"
        and restored_weights == trained_weights
    )
    return {
        "benchmark": "mnn_bounded_structural_growth",
        "version": 1,
        "initial_weight": weight,
        "baseline_response_to_cue": baseline,
        "grown_connections": grown_edges,
        "trained_response_to_cue": trained,
        "restored_response_to_cue": restored,
        "trained_weights": trained_weights,
        "restored_weights": restored_weights,
        "weights_preserved": restored_weights == trained_weights,
        "passed": passed,
        "interpretation": (
            "Training exposes cue and response together; growth adds one edge. "
            "Evaluation provides only the cue. This demonstrates a bounded "
            "structural association with teacher forcing, not autonomous "
            "discovery, general learning, or intelligence."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
