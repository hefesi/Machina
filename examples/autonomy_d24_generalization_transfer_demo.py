"""D2.4: evaluate strategy transfer on task formats withheld from training."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.adaptive_learning import AdaptiveStrategyLearner
from machina.skill_benchmark import score
from machina.transfer_benchmark import TRANSFER_TASKS, score_transfer, solve_transfer
from examples.autonomy_d22_useful_skill_demo import STRATEGIES, TRAINING_TASKS, _mean


def run_demo() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "d24_transfer.sqlite3"
        learner = AdaptiveStrategyLearner(database)

        observations = 0
        for task in TRAINING_TASKS:
            for strategy in STRATEGIES:
                learner.record_outcome(task.task_type, strategy, score(task, strategy))
                observations += 1

        learned_stats = {
            task_type: learner.strategy_stats(task_type)
            for task_type in sorted({task.task_type for task in TRAINING_TASKS})
        }
        learner.close()

        # Restart: evaluation task families and syntactic formats were not trained.
        learner = AdaptiveStrategyLearner(database)
        results = []
        for task in TRANSFER_TASKS:
            strategy = learner.choose_strategy(task.task_type, STRATEGIES)
            prediction = solve_transfer(task, strategy)
            reward = score_transfer(task, strategy)
            results.append({
                "task_type": task.task_type,
                "question": task.question,
                "chosen_strategy": strategy,
                "prediction": prediction,
                "expected": task.expected_answer,
                "reward": reward,
            })
        persisted = learner.summary()
        learner.close()

        fixed_scores = [score_transfer(task, "direct") for task in TRANSFER_TASKS]
        with tempfile.TemporaryDirectory() as empty_directory:
            cold = AdaptiveStrategyLearner(Path(empty_directory) / "cold.sqlite3")
            cold_scores = [
                score_transfer(task, cold.choose_strategy(task.task_type, STRATEGIES))
                for task in TRANSFER_TASKS
            ]
            cold.close()

    adaptive_accuracy = _mean([float(row["reward"]) for row in results])
    direct_accuracy = _mean(fixed_scores)
    cold_accuracy = _mean(cold_scores)
    passed = (
        observations == 18
        and persisted["trials"] == 18
        and len(results) == 4
        and adaptive_accuracy == 1.0
        and adaptive_accuracy > direct_accuracy
        and adaptive_accuracy > cold_accuracy
        and all(row["chosen_strategy"] == "decompose" for row in results)
    )
    return {
        "experiment": "d2_4_generalization_and_transfer",
        "training_observations": observations,
        "unseen_task_families": sorted({task.task_type for task in TRANSFER_TASKS}),
        "held_out_tasks": len(TRANSFER_TASKS),
        "selected_strategies": [row["chosen_strategy"] for row in results],
        "results": results,
        "adaptive_transfer_accuracy": round(adaptive_accuracy, 4),
        "fixed_direct_baseline_accuracy": round(direct_accuracy, 4),
        "cold_no_memory_baseline_accuracy": round(cold_accuracy, 4),
        "persisted_experience": persisted,
        "training_strategy_stats": learned_stats,
        "passed": passed,
        "scope": (
            "Tests narrow structural transfer: global strategy evidence learned on "
            "prose and pipe tables is reused for unseen question phrasing and two "
            "new record syntaxes. It does not establish broad semantic generalization."
        ),
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)
