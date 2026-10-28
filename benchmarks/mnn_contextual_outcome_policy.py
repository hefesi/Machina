"""Deterministic smoke benchmark for evidence-grounded contextual outcomes.

Run with: python benchmarks/mnn_contextual_outcome_policy.py
Synthetic data validates the decision contract, not generalization or causality.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_contextual_outcome_policy import MNNContextualOutcomePolicy


def add(memory, identifier, action, reward, context, decision=None):
    memory.add(
        f"Observed {action} reward {reward} in {context}",
        kind="action-outcome",
        source_uri=f"benchmark://{identifier}",
        confidence=1.0,
        tags=("action-learning", action),
        metadata={"action": action, "reward": reward, "context": context, **({"decision": decision} if decision is not None else {})},
        fragment_id=identifier,
    )


def run() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        with FragmentMemory(Path(directory) / "outcomes.sqlite3") as memory:
            for index, reward in enumerate((1.0, 0.9, 1.0)):
                add(memory, f"stable-continue-{index}", "continue", reward, "stable workload")
            for index, reward in enumerate((0.0, 0.1, 0.0)):
                add(memory, f"stable-pause-{index}", "pause", reward, "stable workload")
            for index, reward in enumerate((0.0, 0.1, 0.0)):
                add(memory, f"risk-continue-{index}", "continue", reward, "risky workload")
            for index, reward in enumerate((1.0, 0.9, 1.0)):
                add(memory, f"risk-pause-{index}", "pause", reward, "risky workload")

            policy = MNNContextualOutcomePolicy(
                memory, ["continue", "pause"], min_samples_per_action=2,
                min_reward_margin=0.2,
            )
            results = {
                "stable_workload": policy.recommend("stable workload"),
                "risky_workload": policy.recommend("risky workload"),
                "unseen_context": policy.recommend("unseen environment"),
            }
            # Reward reversal: the preferred action changes after decision four.
            # Both policies inspect the same archive; only temporal weighting differs.
            for index in range(1, 5):
                add(memory, f"drift-old-continue-{index}", "continue", 1.0,
                    "changing workload", decision=index)
                add(memory, f"drift-old-pause-{index}", "pause", 0.0,
                    "changing workload", decision=index)
            for index in range(5, 9):
                add(memory, f"drift-new-continue-{index}", "continue", 0.0,
                    "changing workload", decision=index)
                add(memory, f"drift-new-pause-{index}", "pause", 1.0,
                    "changing workload", decision=index)
            drift = {
                "all_history": MNNContextualOutcomePolicy(
                    memory, ["continue", "pause"], min_samples_per_action=2,
                    min_reward_margin=0.2,
                ).recommend("changing workload"),
                "recency_weighted": MNNContextualOutcomePolicy(
                    memory, ["continue", "pause"], min_samples_per_action=2,
                    min_reward_margin=0.2, recency_half_life_decisions=2.0,
                ).recommend("changing workload"),
            }
            return {
                "benchmark": "mnn-contextual-outcome-policy",
                "limitations": [
                    "synthetic rewards and contexts are hand-authored",
                    "lexical association does not establish causation",
                    "no claim of generalization to real environments",
                ],
                "reward_reversal": {
                    name: {"status": result["status"], "action": result.get("action"),
                           "sample_counts": result.get("sample_counts")}
                    for name, result in drift.items()
                },
                "scenarios": {
                    name: {
                        "status": result["status"],
                        "reason": result["reason"],
                        "action": result.get("action"),
                        "sample_counts": result.get("sample_counts"),
                    }
                    for name, result in results.items()
                },
            }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
