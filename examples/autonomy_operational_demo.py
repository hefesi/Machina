"""Reproducible demonstration of bounded operational autonomy feedback.

Run from the repository root:
    python -m examples.autonomy_operational_demo

This experiment tests a narrow claim: explicit outcome feedback changes future
goal ranking, and that adjustment survives reopening the SQLite store. It does
not demonstrate general intelligence or consciousness.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.autonomy import AutonomyController, AutonomyExperienceStore, GoalCandidate


def candidate(goal_id: str, drive: str) -> GoalCandidate:
    return GoalCandidate(
        goal_id=goal_id,
        description=f"Evaluate strategy {goal_id}",
        drive=drive,
        urgency=0.5,
        expected_benefit=0.5,
        confidence=0.5,
        estimated_cost=0.1,
        risk=0.05,
    )


def run_demo() -> dict[str, object]:
    controller = AutonomyController()
    strategy_a = candidate("strategy_a", "strategy_a")
    strategy_b = candidate("strategy_b", "strategy_b")

    baseline = controller.choose([strategy_a, strategy_b])
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "autonomy.sqlite3"
        store = AutonomyExperienceStore(database)
        # Simulate four independently evaluated successful outcomes for B.
        for _ in range(4):
            store.record_selection(strategy_b)
            store.record_feedback("success")
        store.close()

        # Reopen to verify the learned preference came from persistent storage.
        reopened = AutonomyExperienceStore(database)
        adjustments = reopened.drive_adjustments()
        after_learning = controller.choose(
            [strategy_a, strategy_b], drive_adjustments=adjustments
        )
        summary = reopened.summary()
        reopened.close()

    return {
        "experiment": "bounded_operational_autonomy_feedback",
        "baseline_selected": baseline.selected_goal.goal_id if baseline.selected_goal else None,
        "selected_after_feedback_and_restart": (
            after_learning.selected_goal.goal_id if after_learning.selected_goal else None
        ),
        "persistent_adjustments": adjustments,
        "recorded_outcomes": summary,
        "passed": (
            baseline.selected_goal is not None
            and baseline.selected_goal.goal_id == "strategy_a"
            and after_learning.selected_goal is not None
            and after_learning.selected_goal.goal_id == "strategy_b"
            and adjustments.get("strategy_b", 0.0) > 0
        ),
        "scope": (
            "Demonstrates a small persistent preference update from explicit feedback; "
            "not general learning, autonomous task completion, or consciousness."
        ),
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)
