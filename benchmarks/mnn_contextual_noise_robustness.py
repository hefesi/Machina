"""Multi-seed noisy-reward evaluation for lexical context transfer.

Run from the repository root:
    python -m benchmarks.mnn_contextual_noise_robustness

This is a controlled synthetic bandit task, not a natural-language benchmark.
"""
from __future__ import annotations

import random
from typing import Any

from machina.mnn_contextual_action_learning import MNNContextualActionLearner


def _reward(rng: random.Random, probability: float) -> float:
    return 1.0 if rng.random() < probability else 0.0


def run_benchmark(
    *, seeds: int = 20, observations_per_action: int = 24
) -> dict[str, Any]:
    if isinstance(seeds, bool) or not isinstance(seeds, int) or seeds < 1:
        raise ValueError("seeds must be a positive integer")
    if (
        isinstance(observations_per_action, bool)
        or not isinstance(observations_per_action, int)
        or observations_per_action < 1
    ):
        raise ValueError("observations_per_action must be a positive integer")

    cases = (
        ("quiet workload", "quiet workload today", "left"),
        ("busy workload", "busy workload today", "right"),
    )
    exact_correct = exact_recommended = 0
    generalized_correct = generalized_recommended = 0
    records = []

    for seed in range(seeds):
        rng = random.Random(seed)
        exact = MNNContextualActionLearner(
            ["left", "right"], min_samples_per_action=2,
            min_context_similarity=1.0,
        )
        generalized = MNNContextualActionLearner(
            ["left", "right"], min_samples_per_action=2,
            min_context_similarity=0.6,
        )
        for training_context, _, preferred in cases:
            for action in ("left", "right"):
                probability = 0.8 if action == preferred else 0.2
                for _ in range(observations_per_action):
                    reward = _reward(rng, probability)
                    exact.observe(training_context, action, reward)
                    generalized.observe(training_context, action, reward)

        seed_records = []
        for _, query_context, expected in cases:
            for name, learner in (("exact", exact), ("generalized", generalized)):
                result = learner.recommend(query_context)
                recommended = result["status"] == "recommended"
                correct = recommended and result["action"] == expected
                if name == "exact":
                    exact_recommended += int(recommended)
                    exact_correct += int(correct)
                else:
                    generalized_recommended += int(recommended)
                    generalized_correct += int(correct)
                seed_records.append({
                    "query_context": query_context,
                    "expected_action": expected,
                    "model": name,
                    "status": result["status"],
                    "action": result.get("action"),
                    "correct": bool(correct),
                })
        records.append({"seed": seed, "cases": seed_records})

    total_cases = seeds * len(cases)
    return {
        "benchmark": "noisy_lexical_context_transfer",
        "synthetic_only": True,
        "seeds": seeds,
        "observations_per_action_context": observations_per_action,
        "reward_probabilities": {"preferred_action": 0.8, "other_action": 0.2},
        "exact_match": {
            "coverage": exact_recommended / total_cases,
            "accuracy_when_recommended": (
                exact_correct / exact_recommended if exact_recommended else None
            ),
            "recommendations": exact_recommended,
            "abstentions": total_cases - exact_recommended,
        },
        "generalized": {
            "coverage": generalized_recommended / total_cases,
            "accuracy_when_recommended": (
                generalized_correct / generalized_recommended
                if generalized_recommended else None
            ),
            "correct_recommendations": generalized_correct,
            "recommendations": generalized_recommended,
            "abstentions": total_cases - generalized_recommended,
        },
        "records": records,
        "limitations": [
            "Contexts are manually constructed token sets with lexical overlap.",
            "Rewards are synthetic Bernoulli samples.",
            "This does not establish semantic understanding or real-world generalization.",
        ],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_benchmark(), indent=2, sort_keys=True))
