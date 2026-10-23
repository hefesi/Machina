"""Test a tiny MNN on feature combinations absent from training.

Training sees only aligned feature pairs (-1,-1) and (+1,+1). Evaluation
contains mixed-sign combinations with unequal magnitudes, where the correct
class is determined by the sign of the feature sum. This is a narrow test of
composition in a linear association, not a general reasoning benchmark.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_checkpoint import MNNCheckpointStore


TRAINING_EXAMPLES = (
    (-1.0, -1.0, -1),
    (1.0, 1.0, 1),
)
HELD_OUT_EXAMPLES = (
    (1.0, -0.25, 1),
    (0.25, -1.0, -1),
    (-0.25, 1.0, 1),
    (-1.0, 0.25, -1),
    (0.75, -0.25, 1),
    (-0.75, 0.25, -1),
)


def make_network() -> MNN:
    network = MNN(weight_limit=5.0)
    network.add_unit(Unit("feature_a", activation="identity"))
    network.add_unit(Unit("feature_b", activation="identity"))
    network.add_unit(Unit("response", activation="identity"))
    network.add_connection(Connection("a_to_response", "feature_a", "response", 0.0))
    network.add_connection(Connection("b_to_response", "feature_b", "response", 0.0))
    return network


def _predict(network: MNN, feature_a: float, feature_b: float) -> float:
    network.reset_states()
    inputs = {"feature_a": feature_a, "feature_b": feature_b}
    network.step(inputs)
    return network.step(inputs)["response"]


def _evaluate(network: MNN) -> dict[str, Any]:
    rows = []
    for feature_a, feature_b, target in HELD_OUT_EXAMPLES:
        output = _predict(network, feature_a, feature_b)
        predicted = 1 if output > 0 else -1
        rows.append({
            "feature_a": feature_a,
            "feature_b": feature_b,
            "target_class": target,
            "output": output,
            "predicted_class": predicted,
            "correct": predicted == target,
        })
    return {
        "sample_count": len(rows),
        "accuracy": sum(row["correct"] for row in rows) / len(rows),
        "predictions": rows,
    }


def run_benchmark(
    *,
    checkpoint_path: str | Path | None = None,
    learning_rate: float = 0.25,
) -> dict[str, Any]:
    """Train aligned pairs and evaluate mixed feature combinations."""
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise ValueError("learning_rate must be a finite positive number")
    learning_rate = float(learning_rate)
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning_rate must be a finite positive number")

    network = make_network()
    baseline = _evaluate(MNN.from_snapshot(network.snapshot()))

    for feature_a, feature_b, target in TRAINING_EXAMPLES:
        network.reset_states()
        network.step({
            "feature_a": feature_a,
            "feature_b": feature_b,
            "response": float(target),
        })
        network.apply_hebbian(learning_rate=learning_rate, reward=1.0)

    trained_weights = {key: edge.weight for key, edge in network.connections.items()}
    trained = _evaluate(MNN.from_snapshot(network.snapshot()))

    if checkpoint_path is None:
        with tempfile.TemporaryDirectory() as directory:
            store = MNNCheckpointStore(Path(directory) / "composition-checkpoint.json")
            store.save(network)
            restored_network = store.load()
    else:
        store = MNNCheckpointStore(checkpoint_path)
        store.save(network)
        restored_network = store.load()

    restored_weights = {key: edge.weight for key, edge in restored_network.connections.items()}
    restored = _evaluate(restored_network)
    passed = (
        baseline["accuracy"] == 0.5
        and trained["accuracy"] == 1.0
        and restored["predictions"] == trained["predictions"]
        and restored_weights == trained_weights
        and all(
            (feature_a, feature_b) not in ((-1.0, -1.0), (1.0, 1.0))
            for feature_a, feature_b, _ in HELD_OUT_EXAMPLES
        )
    )
    return {
        "benchmark": "mnn_held_out_feature_composition",
        "version": 1,
        "training_examples": [
            {"feature_a": a, "feature_b": b, "target_class": target}
            for a, b, target in TRAINING_EXAMPLES
        ],
        "held_out_examples": [
            {"feature_a": a, "feature_b": b, "target_class": target}
            for a, b, target in HELD_OUT_EXAMPLES
        ],
        "learning_rate": learning_rate,
        "fixed_weights_baseline": baseline,
        "trained_network": trained,
        "checkpoint_restored_network": restored,
        "trained_weights": trained_weights,
        "restored_weights": restored_weights,
        "weights_preserved": restored_weights == trained_weights,
        "passed": passed,
        "interpretation": (
            "This tests a few unseen mixed feature combinations in a simple "
            "linearly separable task. It does not demonstrate broad compositional "
            "reasoning, task transfer, semantic understanding, consciousness, "
            "or general intelligence."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
