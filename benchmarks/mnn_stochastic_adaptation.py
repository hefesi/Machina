"""Multi-seed noisy-reward benchmark for MNN action learning.

Run from the repository root:
    python -m benchmarks.mnn_stochastic_adaptation

This is a synthetic two-action bandit with a reward reversal. It measures
adaptation under stochastic outcomes; it does not test semantic understanding,
general intelligence, or real-world autonomy.
"""
from __future__ import annotations

import json
import random
from statistics import mean
from typing import Any

from machina.mnn_action_learning import MNNActionLearner


ACTIONS = ("left", "right")


def _reward_probability(action: str, *, reversed_environment: bool) -> float:
    preferred = "right" if reversed_environment else "left"
    return 0.8 if action == preferred else 0.2


def _run_seed(seed: int, *, trials_per_phase: int) -> dict[str, Any]:
    environment = random.Random(seed * 7919 + 17)
    baseline_environment = random.Random(seed * 7919 + 31)
    baseline_policy = random.Random(seed * 7919 + 47)
    learner = MNNActionLearner(
        list(ACTIONS),
        learning_rate=0.2,
        exploration_interval=5,
        exploration_seed=seed,
    )
    rewards: list[float] = []
    baseline_rewards: list[float] = []

    for index in range(trials_per_phase * 2):
        reversed_environment = index >= trials_per_phase
        action = learner.choose(epsilon=0.15)
        probability = _reward_probability(action, reversed_environment=reversed_environment)
        reward = float(environment.random() < probability)
        learner.observe(reward)
        rewards.append(reward)

        baseline_action = baseline_policy.choice(ACTIONS)
        baseline_probability = _reward_probability(
            baseline_action, reversed_environment=reversed_environment
        )
        baseline_rewards.append(float(baseline_environment.random() < baseline_probability))

    phase_1 = rewards[:trials_per_phase]
    phase_2 = rewards[trials_per_phase:]
    adaptation_window = min(30, trials_per_phase)
    tail_window = min(60, trials_per_phase)
    return {
        "seed": seed,
        "phase_1_reward_rate": mean(phase_1),
        "phase_2_first_30_reward_rate": mean(phase_2[:adaptation_window]),
        "phase_2_last_60_reward_rate": mean(phase_2[-tail_window:]),
        "random_baseline_reward_rate": mean(baseline_rewards),
        "final_predictions": learner.predictions(),
        "final_action_counts": dict(learner.counts),
    }


def run_benchmark(*, seeds: int = 20, trials_per_phase: int = 120) -> dict[str, Any]:
    """Compare seeded epsilon-greedy learning with a random-action baseline."""
    if isinstance(seeds, bool) or not isinstance(seeds, int) or seeds < 5:
        raise ValueError("seeds must be an integer of at least 5")
    if (
        isinstance(trials_per_phase, bool)
        or not isinstance(trials_per_phase, int)
        or trials_per_phase < 60
    ):
        raise ValueError("trials_per_phase must be an integer of at least 60")

    results = [_run_seed(seed, trials_per_phase=trials_per_phase) for seed in range(seeds)]
    phase_1_rate = mean(item["phase_1_reward_rate"] for item in results)
    adaptation_rate = mean(item["phase_2_last_60_reward_rate"] for item in results)
    baseline_rate = mean(item["random_baseline_reward_rate"] for item in results)
    early_after_shift = mean(item["phase_2_first_30_reward_rate"] for item in results)
    passed = (
        phase_1_rate >= 0.68
        and adaptation_rate >= 0.65
        and adaptation_rate >= baseline_rate + 0.10
    )
    return {
        "benchmark": "mnn_stochastic_adaptation",
        "version": 1,
        "environment": {
            "type": "two-action Bernoulli bandit",
            "preferred_action_phase_1": "left",
            "preferred_action_phase_2": "right",
            "reward_probabilities": {"preferred": 0.8, "other": 0.2},
            "seeds": seeds,
            "trials_per_phase": trials_per_phase,
        },
        "aggregate": {
            "phase_1_reward_rate": phase_1_rate,
            "phase_2_first_30_reward_rate": early_after_shift,
            "phase_2_last_60_reward_rate": adaptation_rate,
            "random_baseline_reward_rate": baseline_rate,
            "adaptation_minus_random_baseline": adaptation_rate - baseline_rate,
        },
        "criteria": {
            "phase_1_reward_rate_at_least_0_68": phase_1_rate >= 0.68,
            "late_phase_2_reward_rate_at_least_0_65": adaptation_rate >= 0.65,
            "late_phase_2_beats_random_by_0_10": adaptation_rate >= baseline_rate + 0.10,
        },
        "per_seed": results,
        "passed": passed,
        "interpretation": (
            "A passing result supports adaptation to a reward reversal in this noisy, "
            "synthetic two-action task across the tested seeds. It does not establish "
            "semantic learning, transfer to unseen tasks, causal reasoning, consciousness, "
            "or real-world autonomy."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
