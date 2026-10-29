"""Evaluate whether archived context changes the selected action.

Run from the repository root:
    python -m benchmarks.mnn_contextual_policy

The synthetic task deliberately reverses the best action by context. It tests
context-conditioned recommendations from recorded outcomes, not semantic
understanding, causal inference, or general intelligence.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from machina.fragment_memory import FragmentMemory
from machina.mnn_contextual_outcome_policy import MNNContextualOutcomePolicy


def run_benchmark(*, samples_per_action_context: int = 3) -> dict[str, Any]:
    """Seed balanced contextual evidence and score held-out context queries."""
    if (
        isinstance(samples_per_action_context, bool)
        or not isinstance(samples_per_action_context, int)
        or samples_per_action_context < 2
    ):
        raise ValueError("samples_per_action_context must be an integer of at least 2")

    with tempfile.TemporaryDirectory() as directory:
        with FragmentMemory(Path(directory) / "memory.sqlite3") as memory:
            expected = {"quiet workload": "left", "busy workload": "right"}
            index = 0
            for context, preferred in expected.items():
                for action in ("left", "right"):
                    reward = 1.0 if action == preferred else 0.0
                    for _ in range(samples_per_action_context):
                        index += 1
                        memory.add(
                            f"Observed {action} under {context}; reward {reward:g}.",
                            kind="action-outcome",
                            source_uri=f"benchmark://contextual-policy/{index}",
                            confidence=1.0,
                            tags=("action-learning", action),
                            metadata={
                                "action": action,
                                "reward": reward,
                                "context": context,
                                "decision": index,
                            },
                        )

            policy = MNNContextualOutcomePolicy(
                memory,
                ["left", "right"],
                min_samples_per_action=samples_per_action_context,
                min_reward_margin=0.1,
                min_context_overlap=0.6,
            )
            results = {
                context: policy.recommend(context)
                for context in expected
            }
            correct = sum(
                results[context].get("action") == action
                for context, action in expected.items()
            )
            # A context-free policy sees a balanced global reward history. A
            # fixed tie-break therefore gets one of these two contexts correct.
            global_baseline_accuracy = 0.5
            contextual_accuracy = correct / len(expected)
            passed = (
                all(result.get("status") == "recommended" for result in results.values())
                and contextual_accuracy > global_baseline_accuracy
                and contextual_accuracy == 1.0
            )
            return {
                "benchmark": "mnn_contextual_policy",
                "version": 1,
                "samples_per_action_context": samples_per_action_context,
                "context_results": results,
                "contextual_accuracy": contextual_accuracy,
                "context_free_baseline_accuracy": global_baseline_accuracy,
                "memory_records": memory.count(),
                "passed": passed,
                "interpretation": (
                    "The policy selects different actions for two lexical contexts "
                    "from balanced archived outcomes. This validates the configured "
                    "context-overlap and reward-evidence mechanism; it does not show "
                    "that the MNN itself learned language semantics or that the "
                    "recommendations generalize beyond these controlled contexts."
                ),
            }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
