"""D2 experiment: objective feedback improves strategy choice and survives restart.

Run:
    python -m pip install -e .
    python -m examples.autonomy_adaptive_learning_demo
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.adaptive_learning import AdaptiveStrategyLearner


TASKS = {
    "numeric_reasoning": {
        "strategies": ("direct", "calculation", "checklist"),
        "rewards": {"direct": 0.35, "calculation": 1.0, "checklist": 0.50},
    },
    "information_organization": {
        "strategies": ("direct", "decompose", "checklist"),
        "rewards": {"direct": 0.40, "decompose": 1.0, "checklist": 0.55},
    },
}


def run_demo() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "adaptive.sqlite3"
        learner = AdaptiveStrategyLearner(database)
        training_records: list[dict[str, object]] = []

        # The environment evaluates outcomes using a fixed, explicit rubric.
        # The learner never receives the answer key, only the scalar reward.
        for _ in range(6):
            for task_type, task in TASKS.items():
                strategy = learner.choose_strategy(task_type, task["strategies"])
                reward = task["rewards"][strategy]
                learner.record_outcome(task_type, strategy, reward)
                training_records.append({
                    "task_type": task_type,
                    "strategy": strategy,
                    "reward": reward,
                })
        before_restart_stats = {
            task_type: learner.strategy_stats(task_type) for task_type in TASKS
        }
        learner.close()

        # Restart and evaluate on fresh task instances with no further training.
        learner = AdaptiveStrategyLearner(database)
        adaptive_scores: list[float] = []
        fixed_baseline_scores: list[float] = []
        post_restart_choices: dict[str, str] = {}
        for task_type, task in TASKS.items():
            strategy = learner.choose_strategy(task_type, task["strategies"])
            post_restart_choices[task_type] = strategy
            adaptive_scores.extend([task["rewards"][strategy]] * 3)
            fixed_baseline_scores.extend([task["rewards"]["direct"]] * 3)
        persistent_stats = {
            task_type: learner.strategy_stats(task_type) for task_type in TASKS
        }
        summary = learner.summary()
        learner.close()

    adaptive_mean = sum(adaptive_scores) / len(adaptive_scores)
    baseline_mean = sum(fixed_baseline_scores) / len(fixed_baseline_scores)
    passed = (
        post_restart_choices == {
            "numeric_reasoning": "calculation",
            "information_organization": "decompose",
        }
        and adaptive_mean > baseline_mean
        and summary["trials"] == 12
    )
    return {
        "experiment": "d2_adaptive_strategy_learning",
        "training_trials": len(training_records),
        "post_restart_choices": post_restart_choices,
        "persisted_strategy_stats": persistent_stats,
        "training_strategy_stats": before_restart_stats,
        "adaptive_mean_reward": round(adaptive_mean, 4),
        "fixed_direct_baseline_mean_reward": round(baseline_mean, 4),
        "improvement": round(adaptive_mean - baseline_mean, 4),
        "summary": summary,
        "passed": passed,
        "scope": (
            "Shows adaptation to a fixed synthetic task rubric, objective reward "
            "feedback, task-type-specific strategy estimates, and SQLite persistence. "
            "It does not show open-ended learning, transfer to real tasks, or consciousness."
        ),
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)
