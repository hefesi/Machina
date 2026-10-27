"""Compare immediate Hebbian learning with delayed reward eligibility.

Run from the repository root:
    python -m benchmarks.mnn_delayed_reward

This is a deterministic mechanism-level experiment, not a claim of biological
fidelity, semantic reasoning, or consciousness.
"""
from __future__ import annotations

import json
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_reward import RewardModulator


def make_network() -> MNN:
    network = MNN(weight_limit=2.0)
    network.add_unit(Unit("action", activation="identity"))
    network.add_unit(Unit("outcome", activation="identity"))
    network.add_connection(Connection("action_to_outcome", "action", "outcome", 0.5))
    network.units["action"].state = 1.0
    network.units["outcome"].state = 1.0
    return network


def run_benchmark(*, learning_rate: float = 0.1, delay_steps: int = 3) -> dict[str, Any]:
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise ValueError("learning_rate must be a finite non-negative number")
    if learning_rate < 0:
        raise ValueError("learning_rate cannot be negative")
    if isinstance(delay_steps, bool) or not isinstance(delay_steps, int) or delay_steps < 1:
        raise ValueError("delay_steps must be an integer >= 1")

    immediate = make_network()
    delayed = make_network()
    modulator = RewardModulator(trace_decay=0.9, baseline_rate=0.1)

    initial_weight = delayed.connections["action_to_outcome"].weight

    # The causal activity occurs first. The modulator records eligibility while
    # the reward is neutral; subsequent steps contain no co-activity.
    modulator.update(delayed, reward=0.0, learning_rate=float(learning_rate))
    for _ in range(delay_steps):
        delayed.units["action"].state = 0.0
        delayed.units["outcome"].state = 0.0
        modulator.update(delayed, reward=0.0, learning_rate=float(learning_rate))

    # At reward time the baseline method sees no co-activity; the trace method
    # still retains a decayed eligibility trace from the earlier event.
    immediate.units["action"].state = 0.0
    immediate.units["outcome"].state = 0.0
    immediate.apply_hebbian(learning_rate=float(learning_rate), reward=1.0)
    delayed_changes = modulator.update(
        delayed, reward=1.0, learning_rate=float(learning_rate)
    )

    immediate_weight = immediate.connections["action_to_outcome"].weight
    delayed_weight = delayed.connections["action_to_outcome"].weight
    trace = modulator.eligibility.get("action_to_outcome", 0.0)
    passed = (
        immediate_weight == initial_weight
        and delayed_weight > initial_weight
        and delayed_changes["action_to_outcome"] > 0.0
        and trace > 0.0
    )
    return {
        "benchmark": "mnn_delayed_reward_eligibility",
        "version": 1,
        "learning_rate": float(learning_rate),
        "delay_steps": delay_steps,
        "initial_weight": initial_weight,
        "immediate_hebbian_weight": immediate_weight,
        "eligibility_weight": delayed_weight,
        "eligibility_trace_at_reward": trace,
        "immediate_weight_delta": immediate_weight - initial_weight,
        "eligibility_weight_delta": delayed_weight - initial_weight,
        "passed": passed,
        "interpretation": (
            "In this controlled toy case, a delayed reward changes the weight "
            "only when a prior eligibility trace is retained. This validates "
            "the mechanism's intended behavior, not general task performance "
            "or biological equivalence."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
