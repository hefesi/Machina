"""Compare fixed epsilon exploration with a confidence-bonus policy.

Run from the repository root:
    python benchmarks/mnn_uncertainty_exploration.py

The toy environment deterministically reverses which of two actions is rewarded.
This experiment measures a limited bandit heuristic, not general intelligence.
"""
from __future__ import annotations

import json
import statistics
from typing import Any

from machina.mnn_action_learning import MNNActionLearner

ACTIONS = ("left", "right")
SEEDS = (3, 11, 23, 47, 89)
ROUNDS_PER_PHASE = 100
POLICIES = (
    ("epsilon_greedy", 0.15),
    ("uncertainty_bonus", 0.0),
    ("uncertainty_bonus", 0.2),
    ("uncertainty_bonus", 0.5),
    ("uncertainty_bonus", 1.0),
)


def run_trial(*, policy: str, parameter: float, seed: int, rounds_per_phase: int = ROUNDS_PER_PHASE) -> dict[str, Any]:
    if policy not in ("epsilon_greedy", "uncertainty_bonus"):
        raise ValueError("policy must be 'epsilon_greedy' or 'uncertainty_bonus'")
    if isinstance(rounds_per_phase, bool) or not isinstance(rounds_per_phase, int) or rounds_per_phase < 10:
        raise ValueError("rounds_per_phase must be an integer of at least 10")
    learner = MNNActionLearner(list(ACTIONS), learning_rate=0.3, exploration_seed=seed)
    phases = []
    epsilon_explorations = 0
    uncertainty_overrides = 0
    for preferred in ("left", "right"):
        rewards = []
        for _ in range(rounds_per_phase):
            if policy == "epsilon_greedy":
                action = learner.choose(epsilon=parameter)
            else:
                action = learner.choose(uncertainty_bonus=parameter)
            epsilon_explorations += int(learner.last_selection_mode == "epsilon_explore")
            uncertainty_overrides += int(learner.last_selection_mode == "uncertainty_bonus")
            reward = 1.0 if action == preferred else 0.0
            learner.observe(reward, action=action)
            rewards.append(reward)
        phases.append({
            "preferred_action": preferred,
            "reward_total": sum(rewards),
            "reward_rate": sum(rewards) / len(rewards),
            "rounds": len(rewards),
        })
    return {
        "policy": policy,
        "parameter": float(parameter),
        "seed": seed,
        "phase_1": phases[0],
        "phase_2": phases[1],
        "total_reward": phases[0]["reward_total"] + phases[1]["reward_total"],
        "epsilon_exploration_decisions": epsilon_explorations,
        "uncertainty_override_decisions": uncertainty_overrides,
        "final_predictions": learner.predictions(),
    }


def run_benchmark(
    *, seeds: tuple[int, ...] = SEEDS, rounds_per_phase: int = ROUNDS_PER_PHASE
) -> dict[str, Any]:
    if not seeds or any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("seeds must be a non-empty sequence of integers")
    trials = [
        run_trial(policy=policy, parameter=parameter, seed=seed, rounds_per_phase=rounds_per_phase)
        for policy, parameter in POLICIES for seed in seeds
    ]
    summaries = []
    for policy, parameter in POLICIES:
        group = [item for item in trials if item["policy"] == policy and item["parameter"] == parameter]
        summaries.append({
            "policy": policy,
            "parameter": parameter,
            "seeds": len(group),
            "phase_1_mean_reward_rate": statistics.mean(item["phase_1"]["reward_rate"] for item in group),
            "phase_2_mean_reward_rate": statistics.mean(item["phase_2"]["reward_rate"] for item in group),
            "mean_total_reward": statistics.mean(item["total_reward"] for item in group),
            "mean_epsilon_exploration_decisions": statistics.mean(item["epsilon_exploration_decisions"] for item in group),
            "mean_uncertainty_override_decisions": statistics.mean(item["uncertainty_override_decisions"] for item in group),
        })
    return {
        "benchmark": "mnn_uncertainty_exploration",
        "version": 1,
        "rounds_per_phase": rounds_per_phase,
        "seeds": list(seeds),
        "reward_mapping": {"phase_1": {"left": 1.0, "right": 0.0},
                           "phase_2": {"left": 0.0, "right": 1.0}},
        "summaries": summaries,
        "trials": trials,
        "interpretation": (
            "The confidence bonus adds c * sqrt(log(decisions) / observations_for_action) "
            "to each action's current estimated reward. It is a transparent heuristic; "
            "this benchmark does not prove superiority, calibrated uncertainty, or "
            "generalization to stochastic or contextual environments."
        ),
    }


def main() -> None:
    print(json.dumps(run_benchmark(), indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
