"""Evaluate whether simple MNN learning transfers to unseen input magnitudes.

Run from the repository root:
    python -m benchmarks.mnn_generalization

Training uses only the endpoint examples (-1 -> -1, +1 -> +1). Evaluation
holds out all intermediate magnitudes and compares fixed, trained, and
checkpoint-restored networks. This is a narrow linear-association test.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_checkpoint import MNNCheckpointStore


TRAINING_EXAMPLES = ((-1.0, -1.0), (1.0, 1.0))
HELD_OUT_INPUTS = (-0.75, -0.5, -0.25, 0.25, 0.5, 0.75)


def make_network() -> MNN:
    network = MNN(weight_limit=5.0)
    network.add_unit(Unit("signal", activation="identity"))
    network.add_unit(Unit("response", activation="identity"))
    network.add_connection(Connection("signal_to_response", "signal", "response", 0.0))
    return network


def _predict(network: MNN, signal: float) -> float:
    network.reset_states()
    # MNN updates synchronously, so the second step propagates the clamped signal.
    network.step({"signal": signal})
    return network.step({"signal": signal})["response"]


def _evaluate(network: MNN, inputs: tuple[float, ...]) -> dict[str, Any]:
    rows = []
    for signal in inputs:
        target = 1 if signal > 0 else -1
        output = _predict(network, signal)
        predicted = 1 if output > 0 else -1
        rows.append({
            "input": signal,
            "target_class": target,
            "output": output,
            "predicted_class": predicted,
            "correct": predicted == target,
        })
    return {
        "sample_count": len(rows),
        "accuracy": sum(row["correct"] for row in rows) / len(rows) if rows else 0.0,
        "predictions": rows,
    }


def run_benchmark(
    *,
    checkpoint_path: str | Path | None = None,
    learning_rate: float = 0.25,
) -> dict[str, Any]:
    """Train on endpoints, evaluate unseen intermediate values, and reload."""
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise ValueError("learning_rate must be a finite non-negative number")
    learning_rate = float(learning_rate)
    if not math.isfinite(learning_rate) or learning_rate < 0:
        raise ValueError("learning_rate must be a finite non-negative number")
    if learning_rate == 0:
        raise ValueError("learning_rate must be greater than zero")

    network = make_network()
    fixed_weights = MNN.from_snapshot(network.snapshot())
    baseline = _evaluate(fixed_weights, HELD_OUT_INPUTS)

    for signal, target in TRAINING_EXAMPLES:
        network.reset_states()
        # Clamp the response to the known target for this supervised association.
        network.step({"signal": signal, "response": target})
        network.apply_hebbian(learning_rate=learning_rate, reward=1.0)

    trained_weights = {
        key: edge.weight for key, edge in network.connections.items()
    }
    trained = _evaluate(MNN.from_snapshot(network.snapshot()), HELD_OUT_INPUTS)

    if checkpoint_path is None:
        with tempfile.TemporaryDirectory() as directory:
            store = MNNCheckpointStore(Path(directory) / "generalization-checkpoint.json")
            store.save(network)
            restored_network = store.load()
    else:
        store = MNNCheckpointStore(checkpoint_path)
        store.save(network)
        restored_network = store.load()

    restored_weights = {
        key: edge.weight for key, edge in restored_network.connections.items()
    }
    restored = _evaluate(restored_network, HELD_OUT_INPUTS)
    passed = (
        baseline["accuracy"] == 0.5
        and trained["accuracy"] == 1.0
        and restored["accuracy"] == trained["accuracy"]
        and restored["predictions"] == trained["predictions"]
        and restored_weights == trained_weights
        and all(value not in (-1.0, 1.0) for value in HELD_OUT_INPUTS)
    )
    return {
        "benchmark": "mnn_held_out_magnitude_generalization",
        "version": 1,
        "training_examples": [
            {"input": signal, "target_class": target}
            for signal, target in TRAINING_EXAMPLES
        ],
        "held_out_inputs": list(HELD_OUT_INPUTS),
        "learning_rate": learning_rate,
        "fixed_weights_baseline": baseline,
        "trained_network": trained,
        "checkpoint_restored_network": restored,
        "trained_weights": trained_weights,
        "restored_weights": restored_weights,
        "weights_preserved": restored_weights == trained_weights,
        "passed": passed,
        "interpretation": (
            "This checks interpolation to unseen magnitudes in a one-edge linear "
            "association. It does not test complex compositional transfer, robust "
            "generalization, semantic reasoning, consciousness, or general intelligence."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
