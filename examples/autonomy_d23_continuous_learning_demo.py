"""D2.3: incremental learning, restart persistence, and retention checks."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.adaptive_learning import AdaptiveStrategyLearner
from machina.continuous_learning import evaluate_retention, learn_batch
from machina.skill_benchmark import score, solve
from examples.autonomy_d22_useful_skill_demo import HELD_OUT_TASKS, STRATEGIES, TRAINING_TASKS, _mean


def run_demo() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "continuous.sqlite3"
        learner = AdaptiveStrategyLearner(database)
        prose_tasks = [task for task in TRAINING_TASKS if task.task_type == "prose_lookup"]
        table_tasks = [task for task in TRAINING_TASKS if task.task_type == "table_lookup"]

        first_batch = learn_batch(learner, prose_tasks, STRATEGIES, score)
        first_stats_before = learner.strategy_stats("prose_lookup")
        learner.close()

        # Simulate a later session/process: the first batch must survive.
        learner = AdaptiveStrategyLearner(database)
        second_batch = learn_batch(learner, table_tasks, STRATEGIES, score)
        table_stats = learner.strategy_stats("table_lookup")
        learner.close()

        # Restart again before testing both previously learned task families.
        learner = AdaptiveStrategyLearner(database)
        retained_prose_stats = learner.strategy_stats("prose_lookup")
        retention_results = evaluate_retention(learner, HELD_OUT_TASKS, STRATEGIES, solve, score)
        summary = learner.summary()
        learner.close()

    accuracy = _mean([float(row["reward"]) for row in retention_results])
    prose_retained = retained_prose_stats == first_stats_before and retained_prose_stats.get("decompose", {}).get("mean_reward") == 1.0
    table_learned = table_stats.get("checklist", {}).get("mean_reward") == 1.0
    passed = first_batch == 9 and second_batch == 9 and summary["trials"] == 18 and prose_retained and table_learned and accuracy == 1.0
    return {
        "experiment": "d2_3_continuous_learning_and_retention",
        "incremental_batches": {"prose_first_session_observations": first_batch, "table_later_session_observations": second_batch},
        "persisted_experience_after_two_restarts": summary,
        "prose_strategy_stats_before_later_learning": first_stats_before,
        "prose_strategy_stats_after_later_learning_and_restart": retained_prose_stats,
        "table_strategy_stats_after_later_learning": table_stats,
        "held_out_retention_results": retention_results,
        "held_out_accuracy": round(accuracy, 4),
        "passed": passed,
        "scope": "Shows incremental SQLite-backed experience retention and task-family strategy retention on two narrow retrieval formats. It does not test neural-weight consolidation, broad transfer, or consciousness.",
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)
