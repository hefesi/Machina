"""Reproducible micro-benchmark for reward-modulated MNN plasticity.

Run from the repository root with:
    python -m benchmarks.mnn_reward_learning

This deliberately small associative task checks implementation behavior, not
semantic reasoning, general intelligence, or performance against modern models.
"""
from __future__ import annotations

import json
from typing import Any

from machina.mnn import Connection, MNN, Unit


def make_network() -> MNN:
    network = MNN(weight_limit=5.0)
    network.add_unit(Unit("context_positive", activation="identity"))
    network.add_unit(Unit("context_negative", activation="identity"))
    network.add_unit(Unit("response", activation="sigmoid"))
    network.add_connection(
        Connection("positive_to_response", "context_positive", "response", 0.0)
    )
    network.add_connection(
        Connection("negative_to_response", "context_negative", "response", 0.0)
    )
    return network


def _present(network: MNN, positive_context: bool) -> float:
    inputs = {
        "context_positive": 1.0 if positive_context else 0.0,
        "context_negative": 0.0 if positive_context else 1.0,
    }
    # MNN updates synchronously from the previous state. Two steps ensure the
    # response is computed from the context currently being presented.
    network.step(inputs)
    return network.step(inputs)["response"]


def _evaluate(network: MNN) -> dict[str, Any]:
    network.reset_states()
    cases = (
        (True, 1.0),
        (False, 0.0),
    )
    predictions = []
    squared_errors = []
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
        squared_errors.append((output - target) ** 2)
    return {
        "accuracy": sum(item["correct"] for item in predictions) / len(predictions),
        "mean_squared_error": sum(squared_errors) / len(squared_errors),
        "predictions": predictions,
    }


def run_benchmark(*, training_rounds: int = 8, learning_rate: float = 0.5) -> dict[str, Any]:
    """Compare initial fixed weights with reward-trained weights on two contexts."""
    if isinstance(training_rounds, bool) or not isinstance(training_rounds, int):
        raise ValueError("training_rounds must be an integer")
    if training_rounds < 1:
        raise ValueError("training_rounds must be at least 1")
    if learning_rate < 0:
        raise ValueError("learning_rate must be non-negative")

    trained = make_network()
    baseline = MNN.from_snapshot(trained.snapshot())
    baseline_metrics = _evaluate(baseline)

    # Fixed order and no randomness make runs exactly reproducible.
    for _ in range(training_rounds):
        _present(trained, positive_context=True)
        trained.apply_hebbian(learning_rate=learning_rate, reward=1.0)
        _present(trained, positive_context=False)
        trained.apply_hebbian(learning_rate=learning_rate, reward=-1.0)

    trained_metrics = _evaluate(trained)
    return {
        "benchmark": "two_context_reward_association",
        "version": 1,
        "training_rounds": training_rounds,
        "learning_rate": learning_rate,
        "baseline_fixed_weights": baseline_metrics,
        "trained_reward_plasticity": trained_metrics,
        "final_weights": {
            edge_id: edge.weight for edge_id, edge in trained.connections.items()
        },
        "interpretation": (
            "A deterministic toy association check only; it does not measure "
            "language understanding, reasoning, generalization to unseen tasks, "
            "or AGI. The fixed-weight baseline is not a competitive model."
        ),
    }


def main() -> None:
    print(json.dumps(run_benchmark(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
