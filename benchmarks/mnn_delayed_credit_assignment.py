"""Measure reward credit assignment over delayed MNN activity traces.

Run from the repository root:
    python -m benchmarks.mnn_delayed_credit_assignment

The benchmark is a controlled mechanism test, not evidence of general
intelligence, semantic understanding, or subjective experience.
"""
from __future__ import annotations

import json
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_experience import MNNExperienceCycle


def _run_episode(*, delay_steps: int, reward: float) -> dict[str, Any]:
    network = MNN(weight_limit=2.0)
    network.add_unit(Unit("cue", activation="identity"))
    network.add_unit(Unit("outcome", bias=0.5, activation="identity"))
    network.add_connection(Connection("cue-outcome", "cue", "outcome", 0.25))
    cycle = MNNExperienceCycle(network, learning_rate=0.1)

    initial_weight = network.connections["cue-outcome"].weight
    cycle.step({"cue": 1.0})
    for _ in range(delay_steps):
        cycle.step({"cue": 0.0})
    snapshot = cycle.snapshot()
    restored = MNNExperienceCycle.from_snapshot(snapshot)
    resolved = restored.resolve(reward)
    final_weight = restored.network.connections["cue-outcome"].weight
    return {
        "delay_steps": delay_steps,
        "reward": reward,
        "initial_weight": initial_weight,
        "final_weight": final_weight,
        "weight_change": final_weight - initial_weight,
        "pending_steps_restored": resolved["pending_steps"],
        "traces_cleared_after_resolution": restored.modulator.eligibility == {},
    }


def run_benchmark(*, max_delay_steps: int = 8) -> dict[str, Any]:
    """Verify positive/negative reward signs and attenuation with longer delays."""
    if (
        isinstance(max_delay_steps, bool)
        or not isinstance(max_delay_steps, int)
        or not 1 <= max_delay_steps <= 50
    ):
        raise ValueError("max_delay_steps must be an integer between 1 and 50")

    positive = [_run_episode(delay_steps=delay, reward=1.0)
                for delay in range(max_delay_steps + 1)]
    negative = [_run_episode(delay_steps=delay, reward=-1.0)
                for delay in range(max_delay_steps + 1)]
    positive_magnitudes = [abs(item["weight_change"]) for item in positive]
    criteria = {
        "positive_reward_strengthens_eligible_connection": all(
            item["weight_change"] > 0 for item in positive
        ),
        "negative_reward_weakens_eligible_connection": all(
            item["weight_change"] < 0 for item in negative
        ),
        "longer_delay_attenuates_credit": all(
            positive_magnitudes[index + 1] < positive_magnitudes[index]
            for index in range(len(positive_magnitudes) - 1)
        ),
        "checkpoint_preserves_pending_episode": all(
            item["pending_steps_restored"] == item["delay_steps"] + 1
            for item in positive + negative
        ),
        "traces_clear_after_resolution": all(
            item["traces_cleared_after_resolution"] for item in positive + negative
        ),
    }
    return {
        "benchmark": "mnn_delayed_credit_assignment",
        "version": 1,
        "max_delay_steps": max_delay_steps,
        "positive_reward": positive,
        "negative_reward": negative,
        "criteria": criteria,
        "passed": all(criteria.values()),
        "interpretation": (
            "This checks that reward-modulated eligibility traces can assign a delayed "
            "positive or negative update to a previously active connection, that the "
            "effect attenuates as the trace decays, and that an in-flight episode survives "
            "a JSON-compatible snapshot. It does not validate biological chemistry or "
            "learning in open-ended environments."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
