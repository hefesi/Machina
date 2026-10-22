"""D2.3 helpers for persistent, incremental strategy learning.

The learner reuses D2.1's SQLite experience store. This module adds a small
continual-learning protocol: record each evaluated experience immediately,
retain task-family-specific evidence, and report retention on earlier families
after later families have been learned. It does not implement neural weight
updates or claim general intelligence.
"""
from __future__ import annotations

from collections.abc import Iterable

from machina.adaptive_learning import AdaptiveStrategyLearner


def learn_batch(learner: AdaptiveStrategyLearner, tasks: Iterable[object], strategies: Iterable[str], score_task) -> int:
    """Evaluate all candidates on a batch and persist each reward immediately."""
    count = 0
    options = tuple(strategies)
    if not options:
        raise ValueError("at least one strategy is required")
    for task in tasks:
        task_type = getattr(task, "task_type", None)
        if not isinstance(task_type, str) or not task_type.strip():
            raise ValueError("each task must have a non-empty task_type")
        for strategy in options:
            reward = score_task(task, strategy)
            learner.record_outcome(task_type, strategy, reward)
            count += 1
    return count


def evaluate_retention(learner, tasks, strategies, solve_task, score_task):
    """Evaluate learned strategy selection per task family without changing it."""
    results = []
    for task in tasks:
        strategy = learner.choose_strategy(task.task_type, strategies)
        prediction = solve_task(task, strategy)
        reward = score_task(task, strategy)
        results.append({
            "task_type": task.task_type,
            "question": task.question,
            "strategy": strategy,
            "prediction": prediction,
            "expected": task.expected_answer,
            "reward": reward,
        })
    return results
