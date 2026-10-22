"""Evaluate whether reward learning improves behavior and survives checkpoints.

Run with:
    python -m benchmarks.mnn_learning_retention

This deterministic micro-benchmark tests a narrow association task only. It is
not a benchmark of general intelligence, language, or broad generalization.
"""
from __future__ import annotations

import json
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_learning import EligibilityTraceLearner


def make_network() -> MNN:
    network = MNN(weight_limit=2.0)
    network.add_unit(Unit("positive_context", activation="identity"))
    network.add_unit(Unit("negative_context", activation="identity"))
    network.add_unit(Unit("response", activation="sigmoid"))
    network.add_connection(Connection("positive_to_response", "positive_context", "response", 0.0))
    network.add_connection(Connection("negative_to_response", "negative_context", "response", 0.0))
    return network


def present(network: MNN, positive: bool) -> float:
    inputs = {
        "positive_context": 1.0 if positive else 0.0,
        "negative_context": 0.0 if positive else 1.0,
    }
    network.step(inputs)
    return network.step(inputs)["response"]


def evaluate(network: MNN) -> dict[str, Any]:
    network.reset_states()
    cases = ((True, 1.0), (False, 0.0))
    results = []
    for positive, target in cases:
        output = present(network, positive)
        results.append({
            "context": "positive" if positive else "negative",
            "target": target,
            "output": output,
            "correct": (output >= 0.5) == bool(target),
            "squared_error": (output - target) ** 2,
        })
    return {
        "accuracy": sum(item["correct"] for item in results) / len(results),
        "mean_squared_error": sum(item["squared_error"] for item in results) / len(results),
        "cases": results,
    }


def train_episode(
    network: MNN,
    learner: EligibilityTraceLearner,
    positive: bool,
    reward: float,
) -> None:
    # Preserve co-activity before resetting states to simulate a delayed outcome.
    present(network, positive)
    learner.record_activity()
    network.reset_states()
    learner.apply_reward(reward, clear=True)


def run_benchmark(*, training_rounds: int = 12, learning_rate: float = 0.5) -> dict[str, Any]:
    if isinstance(training_rounds, bool) or not isinstance(training_rounds, int) or training_rounds < 1:
        raise ValueError("training_rounds must be a positive integer")
    if learning_rate < 0:
        raise ValueError("learning_rate must be non-negative")

    baseline = make_network()
    trained = make_network()
    learner = EligibilityTraceLearner(
        trained, learning_rate=learning_rate, trace_decay=0.8, trace_limit=2.0
    )
    before = evaluate(baseline)
    for _ in range(training_rounds):
        train_episode(trained, learner, positive=True, reward=1.0)
        train_episode(trained, learner, positive=False, reward=-1.0)
    after = evaluate(trained)

    # Persist both topology/weights and eligibility state; restore into fresh objects.
    network_checkpoint = trained.snapshot()
    learner_checkpoint = learner.snapshot()
    restored_network = MNN.from_snapshot(network_checkpoint)
    restored_learner = EligibilityTraceLearner(
        restored_network, learning_rate=learning_rate, trace_decay=0.8, trace_limit=2.0
    )
    restored_learner.restore(learner_checkpoint)
    restored = evaluate(restored_network)

    # Verify that serialization preserved the learned parameters, not just outputs.
    weights_before_restart = {
        key: edge.weight for key, edge in trained.connections.items()
    }
    weights_after_restart = {
        key: edge.weight for key, edge in restored_network.connections.items()
    }
    retained = weights_before_restart == weights_after_restart
    same_predictions = [
        item["output"] for item in after["cases"]
    ] == [
        item["output"] for item in restored["cases"]
    ]

    return {
        "benchmark": "mnn_association_learning_and_retention",
        "version": 1,
        "training_rounds": training_rounds,
        "learning_rate": learning_rate,
        "before_training": before,
        "after_training": after,
        "after_checkpoint_restore": restored,
        "retention": {
            "weights_identical": retained,
            "predictions_identical": same_predictions,
            "passed": retained and same_predictions,
        },
        "improvement": {
            "accuracy_delta": after["accuracy"] - before["accuracy"],
            "mean_squared_error_reduction": before["mean_squared_error"] - after["mean_squared_error"],
            "passed": (
                after["accuracy"] > before["accuracy"]
                and after["mean_squared_error"] < before["mean_squared_error"]
            ),
        },
        "interpretation": (
            "Deterministic toy association test only. It does not demonstrate "
            "semantic understanding, broad generalization, reasoning, or AGI."
        ),
    }


def main() -> None:
    print(json.dumps(run_benchmark(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
