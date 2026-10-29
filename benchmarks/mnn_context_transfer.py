"""Measure lexical context transfer against an exact-match baseline.

Run from the repository root:
    python -m benchmarks.mnn_context_transfer

This synthetic evaluation tests lexical transfer only. It is not a semantic
understanding benchmark and does not establish generalization to natural language.
"""
from __future__ import annotations

from typing import Any

from machina.mnn_contextual_action_learning import MNNContextualActionLearner


def _train(learner: MNNContextualActionLearner) -> None:
    for _ in range(4):
        for context, preferred in (
            ("quiet workload", "left"),
            ("busy workload", "right"),
        ):
            for action in ("left", "right"):
                learner.observe(context, action, 1.0 if action == preferred else 0.0)


def _evaluate(learner: MNNContextualActionLearner) -> dict[str, Any]:
    cases = (
        ("quiet workload today", "left"),
        ("busy workload today", "right"),
        ("quiet workload today", "left"),
        ("busy workload today", "right"),
    )
    correct = 0
    recommendations = 0
    abstentions = 0
    records = []
    for context, expected in cases:
        result = learner.recommend(context)
        action = result.get("action")
        if result["status"] == "recommended":
            recommendations += 1
            correct += int(action == expected)
        else:
            abstentions += 1
        records.append({
            "context": context,
            "expected_action": expected,
            "status": result["status"],
            "recommended_action": action,
            "correct": action == expected if action is not None else None,
            "reason": result.get("reason"),
        })
    total = len(cases)
    return {
        "cases": total,
        "recommendations": recommendations,
        "abstentions": abstentions,
        "coverage": recommendations / total,
        "accuracy_when_recommended": correct / recommendations if recommendations else None,
        "correct_recommendations": correct,
        "records": records,
    }


def run_benchmark() -> dict[str, Any]:
    exact = MNNContextualActionLearner(
        ["left", "right"], min_samples_per_action=2, min_context_similarity=1.0
    )
    generalized = MNNContextualActionLearner(
        ["left", "right"], min_samples_per_action=2, min_context_similarity=0.6
    )
    _train(exact)
    _train(generalized)
    return {
        "benchmark": "lexical_context_transfer",
        "synthetic_only": True,
        "exact_match": _evaluate(exact),
        "generalized": _evaluate(generalized),
        "interpretation": (
            "The task tests transfer between token sets with shared words. "
            "It does not test semantic understanding or performance on real-world language."
        ),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(run_benchmark(), indent=2, sort_keys=True))
