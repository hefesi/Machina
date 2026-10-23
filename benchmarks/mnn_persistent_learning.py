"""Check that reward-trained MNN behavior survives checkpoint and restart.

Run from the repository root with:
    python -m benchmarks.mnn_persistent_learning

This deterministic toy association benchmark tests weight persistence and
behavioral retention, not semantic reasoning or general intelligence.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_checkpoint import MNNCheckpointStore


def make_network() -> MNN:
    network = MNN(weight_limit=5.0)
    network.add_unit(Unit("context_positive", activation="identity"))
    network.add_unit(Unit("context_negative", activation="identity"))
    network.add_unit(Unit("response", activation="sigmoid"))
    network.add_connection(Connection(
        "positive_to_response", "context_positive", "response", 0.0
    ))
    network.add_connection(Connection(
        "negative_to_response", "context_negative", "response", 0.0
    ))
    return network


def _present(network: MNN, positive_context: bool) -> float:
    inputs = {
        "context_positive": 1.0 if positive_context else 0.0,
        "context_negative": 0.0 if positive_context else 1.0,
    }
    network.step(inputs)
    return network.step(inputs)["response"]


def _evaluate(network: MNN) -> dict[str, Any]:
    network.reset_states()
    cases = ((True, 1.0), (False, 0.0))
    predictions = []
    errors = []
    for positive_context, target in cases:
        output = _present(network, positive_context)
        predicted = 1.0 if output >= 0.5 else 0.0
        predictions.append({
            "context": "positive" if positive_context else "negative",
            "target": target,
            "output": output,
            "predicted": predicted,
            "correct": predicted == target,
        })
        errors.append((output - target) ** 2)
    return {
        "accuracy": sum(item["correct"] for item in predictions) / len(predictions),
        "mean_squared_error": sum(errors) / len(errors),
        "predictions": predictions,
    }


def run_benchmark(
    *,
    checkpoint_path: str | Path | None = None,
    training_rounds: int = 8,
    learning_rate: float = 0.5,
) -> dict[str, Any]:
    """Train a toy association, persist it, reload it, and test retained behavior."""
    if isinstance(training_rounds, bool) or not isinstance(training_rounds, int):
        raise ValueError("training_rounds must be an integer")
    if training_rounds < 1:
        raise ValueError("training_rounds must be at least 1")
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise ValueError("learning_rate must be a finite non-negative number")
    if learning_rate < 0:
        raise ValueError("learning_rate cannot be negative")

    network = make_network()
    baseline = MNN.from_snapshot(network.snapshot())
    baseline_metrics = _evaluate(baseline)

    # Fixed order and no randomness make the experiment reproducible.
    for _ in range(training_rounds):
        _present(network, positive_context=True)
        network.apply_hebbian(learning_rate=float(learning_rate), reward=1.0)
        _present(network, positive_context=False)
        network.apply_hebbian(learning_rate=float(learning_rate), reward=-1.0)

    trained_metrics = _evaluate(MNN.from_snapshot(network.snapshot()))
    trained_weights = {
        edge_id: edge.weight for edge_id, edge in network.connections.items()
    }

    if checkpoint_path is None:
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = MNNCheckpointStore(Path(directory) / "mnn-checkpoint.json")
            checkpoint.save(network)
            restored = checkpoint.load()
    else:
        checkpoint = MNNCheckpointStore(checkpoint_path)
        checkpoint.save(network)
        restored = checkpoint.load()

    restored_weights = {
        edge_id: edge.weight for edge_id, edge in restored.connections.items()
    }
    restored_metrics = _evaluate(restored)
    passed = (
        baseline_metrics["accuracy"] == 0.5
        and trained_metrics["accuracy"] == 1.0
        and restored_metrics == trained_metrics
        and restored_weights == trained_weights
    )
    return {
        "benchmark": "mnn_reward_learning_checkpoint_restart",
        "version": 1,
        "training_rounds": training_rounds,
        "learning_rate": float(learning_rate),
        "baseline_fixed_weights": baseline_metrics,
        "trained_before_restart": trained_metrics,
        "restored_after_restart": restored_metrics,
        "trained_weights": trained_weights,
        "restored_weights": restored_weights,
        "weights_preserved": restored_weights == trained_weights,
        "passed": passed,
        "interpretation": (
            "A deterministic two-context association shows that learned weights "
            "and measured behavior survive JSON checkpoint reload. This is a "
            "narrow engineering test, not evidence of broad transfer, semantic "
            "understanding, consciousness, or general intelligence."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
