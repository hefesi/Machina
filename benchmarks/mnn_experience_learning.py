"""Learn a small association through delayed experience, then reload it.

Run from the repository root with:
    python -m benchmarks.mnn_experience_learning

Each trial presents a context for two steps, receives a neutral reward, and only
then resolves the outcome. The eligibility traces accumulated during the trial
are credited with the delayed reward. This is a deterministic mechanism test,
not evidence of semantic reasoning, broad generalization, or consciousness.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_experience import MNNExperienceCheckpointStore, MNNExperienceCycle


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


def _inputs(positive_context: bool) -> dict[str, float]:
    return {
        "context_positive": 1.0 if positive_context else 0.0,
        "context_negative": 0.0 if positive_context else 1.0,
    }


def _present(network: MNN, positive_context: bool) -> float:
    inputs = _inputs(positive_context)
    # Synchronous updates need two steps: the first commits the context state,
    # the second computes the response from that context.
    network.step(inputs)
    return network.step(inputs)["response"]


def _evaluate(network: MNN) -> dict[str, Any]:
    probe = MNN.from_snapshot(network.snapshot())
    probe.reset_states()
    predictions = []
    squared_errors = []
    for positive_context, target in ((True, 1.0), (False, 0.0)):
        output = _present(probe, positive_context)
        predicted = 1.0 if output >= 0.5 else 0.0
        predictions.append({
            "context": "positive" if positive_context else "negative",
            "target": target,
            "output": output,
            "predicted": predicted,
            "correct": predicted == target,
        })
        squared_errors.append((output - target) ** 2)
    return {
        "accuracy": sum(item["correct"] for item in predictions) / len(predictions),
        "mean_squared_error": sum(squared_errors) / len(squared_errors),
        "predictions": predictions,
    }


def _train_trial(cycle: MNNExperienceCycle, positive_context: bool, reward: float) -> None:
    cycle.network.reset_states()
    inputs = _inputs(positive_context)
    cycle.step(inputs)
    cycle.step(inputs)
    cycle.resolve(reward)


def run_benchmark(
    *,
    training_rounds: int = 8,
    learning_rate: float = 0.1,
    checkpoint_path: str | Path | None = None,
) -> dict[str, Any]:
    """Train through delayed outcomes, persist, reload, and evaluate retention."""
    if isinstance(training_rounds, bool) or not isinstance(training_rounds, int):
        raise ValueError("training_rounds must be an integer")
    if training_rounds < 1:
        raise ValueError("training_rounds must be at least 1")
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise ValueError("learning_rate must be a finite non-negative number")
    if not math.isfinite(learning_rate) or learning_rate < 0:
        raise ValueError("learning_rate must be finite and non-negative")

    baseline_metrics = _evaluate(make_network())
    cycle = MNNExperienceCycle(make_network(), learning_rate=float(learning_rate))
    for _ in range(training_rounds):
        _train_trial(cycle, True, 1.0)
        _train_trial(cycle, False, -1.0)

    trained_metrics = _evaluate(cycle.network)
    trained_weights = {
        edge_id: edge.weight for edge_id, edge in cycle.network.connections.items()
    }

    if checkpoint_path is None:
        with tempfile.TemporaryDirectory() as directory:
            store = MNNExperienceCheckpointStore(
                Path(directory) / "mnn-experience.json"
            )
            store.save(cycle)
            restored_cycle = store.load()
    else:
        store = MNNExperienceCheckpointStore(checkpoint_path)
        store.save(cycle)
        restored_cycle = store.load()

    restored_metrics = _evaluate(restored_cycle.network)
    restored_weights = {
        edge_id: edge.weight
        for edge_id, edge in restored_cycle.network.connections.items()
    }
    passed = (
        baseline_metrics["accuracy"] == 0.5
        and trained_metrics["accuracy"] == 1.0
        and restored_metrics == trained_metrics
        and restored_weights == trained_weights
        and restored_cycle.pending_steps == 0
    )
    return {
        "benchmark": "mnn_delayed_experience_learning_checkpoint",
        "version": 1,
        "training_rounds": training_rounds,
        "learning_rate": float(learning_rate),
        "baseline_fixed_weights": baseline_metrics,
        "trained_with_delayed_experience": trained_metrics,
        "restored_after_checkpoint": restored_metrics,
        "trained_weights": trained_weights,
        "restored_weights": restored_weights,
        "weights_preserved": restored_weights == trained_weights,
        "pending_steps_after_restore": restored_cycle.pending_steps,
        "passed": passed,
        "interpretation": (
            "A deterministic two-context association shows that outcomes "
            "resolved after the activity can change weights and that the "
            "learned behavior survives a cycle checkpoint reload. This is a "
            "narrow engineering test, not evidence of broad transfer, "
            "semantic understanding, consciousness, or general intelligence."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
