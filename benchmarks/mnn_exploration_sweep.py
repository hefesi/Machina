"""Compare epsilon-greedy exploration under a sudden reward reversal.

Run from the repository root:
    python benchmarks/mnn_exploration_sweep.py

The synthetic environment has two actions and deterministic rewards. This is a
small reproducible diagnostic, not evidence of general intelligence.
"""
from __future__ import annotations

import json
import statistics
from typing import Any

from machina.mnn_action_learning import MNNActionLearner


DEFAULT_EPSILONS = (0.0, 0.05, 0.15, 0.30, 1.0)
DEFAULT_SEEDS = (3, 11, 23, 47, 89)
DEFAULT_ROUNDS_PER_PHASE = 100
ACTIONS = ("left", "right")


def _phase_metrics(rewards: list[float], actions: list[str], learner: MNNActionLearner) -> dict[str, Any]:
    return {
        "rounds": len(rewards),
        "reward_total": sum(rewards),
        "reward_rate": sum(rewards) / len(rewards),
        "action_counts": {name: actions.count(name) for name in ACTIONS},
        "predictions": learner.predictions(),
    }


def _adaptation_lag(rewards: list[float], window: int = 5) -> int | None:
    """Return decisions until the first all-rewarded window; None if not reached."""
    for end in range(window, len(rewards) + 1):
        if all(value == 1.0 for value in rewards[end - window:end]):
            return end
    return None


def run_trial(*, epsilon: float, seed: int, rounds_per_phase: int = DEFAULT_ROUNDS_PER_PHASE) -> dict[str, Any]:
    if isinstance(rounds_per_phase, bool) or not isinstance(rounds_per_phase, int) or rounds_per_phase < 10:
        raise ValueError("rounds_per_phase must be an integer of at least 10")
    learner = MNNActionLearner(
        list(ACTIONS), learning_rate=0.3, exploration_seed=seed,
        exploration_interval=5,
    )

    phase_data = []
    phase_rewards: list[list[float]] = []
    phase_actions: list[list[str]] = []
    exploration_count = 0
    for preferred in ("left", "right"):
        rewards: list[float] = []
        actions: list[str] = []
        for _ in range(rounds_per_phase):
            action = learner.choose(epsilon=epsilon)
            if learner.last_selection_mode == "epsilon_explore":
                exploration_count += 1
            reward = 1.0 if action == preferred else 0.0
            learner.observe(reward)
            actions.append(action)
            rewards.append(reward)
        phase_data.append(_phase_metrics(rewards, actions, learner))
        phase_rewards.append(rewards)
        phase_actions.append(actions)

    return {
        "epsilon": float(epsilon),
        "seed": seed,
        "phase_1_preferred_action": "left",
        "phase_1": phase_data[0],
        "phase_2_preferred_action": "right",
        "phase_2": phase_data[1],
        "phase_2_adaptation_lag": _adaptation_lag(phase_rewards[1]),
        "epsilon_exploration_count": exploration_count,
        "epsilon_exploration_rate": exploration_count / (2 * rounds_per_phase - 2),
        "final_predictions": learner.predictions(),
    }


def run_sweep(
    *, epsilons: tuple[float, ...] = DEFAULT_EPSILONS,
    seeds: tuple[int, ...] = DEFAULT_SEEDS,
    rounds_per_phase: int = DEFAULT_ROUNDS_PER_PHASE,
) -> dict[str, Any]:
    if not epsilons or any(
        isinstance(e, bool) or not isinstance(e, (int, float)) or not 0 <= e <= 1
        for e in epsilons
    ):
        raise ValueError("epsilons must be a non-empty sequence of numbers in [0, 1]")
    if not seeds or any(isinstance(s, bool) or not isinstance(s, int) for s in seeds):
        raise ValueError("seeds must be a non-empty sequence of integers")
    trials = [run_trial(epsilon=float(e), seed=s, rounds_per_phase=rounds_per_phase)
              for e in epsilons for s in seeds]
    summaries = []
    for epsilon in epsilons:
        group = [item for item in trials if item["epsilon"] == float(epsilon)]
        phase1_rates = [item["phase_1"]["reward_rate"] for item in group]
        phase2_rates = [item["phase_2"]["reward_rate"] for item in group]
        lags = [item["phase_2_adaptation_lag"] for item in group]
        observed_lags = [lag for lag in lags if lag is not None]
        exploration_rates = [item["epsilon_exploration_rate"] for item in group]
        summaries.append({
            "epsilon": float(epsilon),
            "seeds": len(group),
            "phase_1_mean_reward_rate": statistics.mean(phase1_rates),
            "phase_2_mean_reward_rate": statistics.mean(phase2_rates),
            "mean_exploration_rate": statistics.mean(exploration_rates),
            "adaptation_successes": len(observed_lags),
            "adaptation_trials": len(group),
            "mean_adaptation_lag_when_reached": (
                statistics.mean(observed_lags) if observed_lags else None
            ),
        })
    return {
        "benchmark": "mnn_epsilon_greedy_exploration_sweep",
        "version": 1,
        "rounds_per_phase": rounds_per_phase,
        "seeds": list(seeds),
        "reward_mapping": {"phase_1": {"left": 1.0, "right": 0.0},
                           "phase_2": {"left": 0.0, "right": 1.0}},
        "summaries": summaries,
        "trials": trials,
        "interpretation": (
            "Compare reward before and after the reversal, actual epsilon-exploration "
            "frequency, and the number of trials that reach five consecutive rewards. "
            "A missing adaptation lag means the criterion was not reached in phase 2. "
            "These are synthetic deterministic bandit results, not a generalization claim."
        ),
    }


def main() -> None:
    print(json.dumps(run_sweep(), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
