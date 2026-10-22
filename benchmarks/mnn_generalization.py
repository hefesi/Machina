"""Held-out generalization benchmark for reward-based MNN learning.

Run from the repository root with:
    python -m benchmarks.mnn_generalization
"""
from __future__ import annotations

import json
import math
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_learning import EligibilityTraceLearner


FEATURES = ("a", "not_a", "b", "not_b")


def make_network() -> MNN:
    network = MNN(weight_limit=4.0)
    for name in FEATURES:
        network.add_unit(Unit(name, activation="identity"))
    network.add_unit(Unit("response", activation="sigmoid"))
    for name in FEATURES:
        network.add_connection(Connection(f"{name}_to_response", name, "response", 0.0))
    return network


def encode(a: bool, b: bool) -> dict[str, float]:
    return {
        "a": float(a),
        "not_a": float(not a),
        "b": float(b),
        "not_b": float(not b),
    }


def present(network: MNN, a: bool, b: bool) -> float:
    inputs = encode(a, b)
    network.step(inputs)
    return network.step(inputs)["response"]


def evaluate(network: MNN, cases: tuple[tuple[bool, bool, float, str], ...]) -> dict[str, Any]:
    network.reset_states()
    rows = []
    for a, b, target, label in cases:
        output = present(network, a, b)
        rows.append({
            "context": label,
            "target": target,
            "output": output,
            "correct": (output >= 0.5) == bool(target),
            "squared_error": (output - target) ** 2,
        })
        network.reset_states()
    return {
        "accuracy": sum(row["correct"] for row in rows) / len(rows),
        "mean_squared_error": sum(row["squared_error"] for row in rows) / len(rows),
        "cases": rows,
    }


def train_reward_episode(
    network: MNN, learner: EligibilityTraceLearner, a: bool, b: bool, reward: float
) -> None:
    present(network, a, b)
    learner.record_activity()
    # The outcome arrives after transient unit states have been cleared.
    network.reset_states()
    learner.apply_reward(reward, clear=True)


def train_hebbian_episode(network: MNN, a: bool, b: bool, reward: float, rate: float) -> None:
    present(network, a, b)
    network.apply_hebbian(learning_rate=rate, reward=reward)
    network.reset_states()


def run_benchmark(*, training_rounds: int = 12, learning_rate: float = 0.5) -> dict[str, Any]:
    if isinstance(training_rounds, bool) or not isinstance(training_rounds, int) or training_rounds < 1:
        raise ValueError("training_rounds must be a positive integer")
    if isinstance(learning_rate, bool):
        raise ValueError("learning_rate must be finite and non-negative")
    try:
        rate = float(learning_rate)
    except (TypeError, ValueError) as error:
        raise ValueError("learning_rate must be finite and non-negative") from error
    if not math.isfinite(rate) or rate < 0:
        raise ValueError("learning_rate must be finite and non-negative")

    # Train only on A-only, B-only, and neither. The A+B conjunction is held out.
    training_cases = (
        (True, False, 1.0, "a_only"),
        (False, True, 1.0, "b_only"),
        (False, False, 0.0, "neither"),
    )
    held_out = ((True, True, 1.0, "a_and_b_unseen"),)
    baseline = make_network()
    reward_net = make_network()
    hebbian_net = make_network()
    learner = EligibilityTraceLearner(
        reward_net, learning_rate=rate, trace_decay=0.8, trace_limit=2.0
    )

    before = evaluate(reward_net, held_out)
    for _ in range(training_rounds):
        for a, b, target, _label in training_cases:
            reward = 1.0 if target == 1.0 else -1.0
            train_reward_episode(reward_net, learner, a, b, reward)
            train_hebbian_episode(hebbian_net, a, b, reward, rate)

    reward_train_metrics = evaluate(reward_net, training_cases)
    reward_held_out = evaluate(reward_net, held_out)
    fixed_held_out = evaluate(baseline, held_out)
    hebbian_held_out = evaluate(hebbian_net, held_out)

    checkpoint = reward_net.snapshot()
    learner_checkpoint = learner.snapshot()
    restored_net = MNN.from_snapshot(checkpoint)
    restored_learner = EligibilityTraceLearner(
        restored_net, learning_rate=rate, trace_decay=0.8, trace_limit=2.0
    )
    restored_learner.restore(learner_checkpoint)
    restored_held_out = evaluate(restored_net, held_out)
    weights_match = {
        key: edge.weight for key, edge in reward_net.connections.items()
    } == {
        key: edge.weight for key, edge in restored_net.connections.items()
    }

    return {
        "benchmark": "mnn_held_out_feature_generalization",
        "version": 1,
        "training_rounds": training_rounds,
        "learning_rate": rate,
        "training_contexts": [label for *_rest, label in training_cases],
        "held_out_contexts": [label for *_rest, label in held_out],
        "training_metrics": reward_train_metrics,
        "held_out": {
            "before_training": before,
            "reward_learning": reward_held_out,
            "fixed_weights": fixed_held_out,
            "immediate_hebbian": hebbian_held_out,
            "checkpoint_restored": restored_held_out,
        },
        "retention": {
            "weights_identical": weights_match,
            "predictions_identical": (
                reward_held_out["cases"] == restored_held_out["cases"]
            ),
            "passed": weights_match and reward_held_out["cases"] == restored_held_out["cases"],
        },
        "generalization": {
            "reward_learning_correct": all(row["correct"] for row in reward_held_out["cases"]),
            "better_than_fixed_weights": (
                reward_held_out["mean_squared_error"] < fixed_held_out["mean_squared_error"]
            ),
            "passed": (
                all(row["correct"] for row in reward_held_out["cases"])
                and reward_held_out["mean_squared_error"] < fixed_held_out["mean_squared_error"]
            ),
        },
        "interpretation": (
            "Small deterministic feature-combination test. It tests transfer to one "
            "held-out conjunction only; it does not establish broad generalization, "
            "reasoning, consciousness, or AGI. Immediate Hebbian learning is a control, "
            "not an independent algorithmic family."
        ),
    }


def main() -> None:
    print(json.dumps(run_benchmark(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
