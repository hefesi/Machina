"""D2.2: learn a useful information-retrieval skill, then test after restart.

Run:
    python -m pip install -e .
    python -m examples.autonomy_d22_useful_skill_demo
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.adaptive_learning import AdaptiveStrategyLearner
from machina.skill_benchmark import RetrievalTask, score, solve


STRATEGIES = ("direct", "decompose", "checklist")

TRAINING_TASKS = (
    RetrievalTask(
        "prose_lookup",
        "Nora's editor is Vim. Ivo's editor is Helix. Nora's room is 12.",
        "What is the editor for Ivo?",
        "Helix",
    ),
    RetrievalTask(
        "prose_lookup",
        "Asha's deadline is 2026-11-03. Beto's deadline is 2026-11-12. Asha's room is 4.",
        "What is the deadline for Beto?",
        "2026-11-12",
    ),
    RetrievalTask(
        "prose_lookup",
        "Lia's room is 8. Omar's room is 17. Lia's editor is Emacs.",
        "What is the room for Omar?",
        "17",
    ),
    RetrievalTask(
        "table_lookup",
        "entity | field | value\nMina | editor | Vim\nRavi | editor | Helix\nMina | room | 5",
        "What is the editor for Ravi?",
        "Helix",
    ),
    RetrievalTask(
        "table_lookup",
        "entity | field | value\nProject Cedar | deadline | 2026-11-04\nProject Quartz | deadline | 2026-11-18",
        "What is the deadline for Project Quartz?",
        "2026-11-18",
    ),
    RetrievalTask(
        "table_lookup",
        "entity | field | value\nSora | room | 2\nTariq | room | 14\nSora | editor | Vim",
        "What is the room for Tariq?",
        "14",
    ),
)

# Held-out records: new entities and answers not present in training.
HELD_OUT_TASKS = (
    RetrievalTask(
        "prose_lookup",
        "Yara's editor is Nano. Paulo's editor is Zed. Yara's room is 3.",
        "What is the editor for Paulo?",
        "Zed",
    ),
    RetrievalTask(
        "prose_lookup",
        "Cleo's deadline is 2026-12-01. Davi's deadline is 2026-12-09.",
        "What is the deadline for Davi?",
        "2026-12-09",
    ),
    RetrievalTask(
        "table_lookup",
        "entity | field | value\nInez | room | 6\nMateo | room | 21\nInez | editor | Vim",
        "What is the room for Mateo?",
        "21",
    ),
    RetrievalTask(
        "table_lookup",
        "entity | field | value\nProject Amber | deadline | 2026-12-02\nProject Indigo | deadline | 2026-12-20",
        "What is the deadline for Project Indigo?",
        "2026-12-20",
    ),
)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def run_demo() -> dict[str, object]:
    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "d22_learning.sqlite3"
        learner = AdaptiveStrategyLearner(database)

        # Controlled exploration: evaluate every candidate on every training task.
        # The evaluator supplies only the scalar reward to the learner.
        training_observations = 0
        for task in TRAINING_TASKS:
            for strategy in STRATEGIES:
                reward = score(task, strategy)
                learner.record_outcome(task.task_type, strategy, reward)
                training_observations += 1

        training_stats = {
            task_type: learner.strategy_stats(task_type)
            for task_type in sorted({task.task_type for task in TRAINING_TASKS})
        }
        learner.close()

        # Reopen the same SQLite file before evaluating held-out records.
        learner = AdaptiveStrategyLearner(database)
        adaptive_results: list[dict[str, object]] = []
        adaptive_scores: list[float] = []
        for task in HELD_OUT_TASKS:
            strategy = learner.choose_strategy(task.task_type, STRATEGIES)
            prediction = solve(task, strategy)
            reward = score(task, strategy)
            adaptive_scores.append(reward)
            adaptive_results.append({
                "task_type": task.task_type,
                "question": task.question,
                "chosen_strategy": strategy,
                "prediction": prediction,
                "expected": task.expected_answer,
                "reward": reward,
            })
        persisted_summary = learner.summary()
        learner.close()

        # Control A: no learning; always use the naive direct strategy.
        fixed_scores = [score(task, "direct") for task in HELD_OUT_TASKS]

        # Control B: fresh learner with an empty database (no retained experience).
        with tempfile.TemporaryDirectory() as empty_directory:
            cold = AdaptiveStrategyLearner(Path(empty_directory) / "empty.sqlite3")
            cold_scores = [
                score(task, cold.choose_strategy(task.task_type, STRATEGIES))
                for task in HELD_OUT_TASKS
            ]
            cold.close()

    adaptive_mean = _mean(adaptive_scores)
    fixed_mean = _mean(fixed_scores)
    cold_mean = _mean(cold_scores)
    passed = (
        training_observations == 18
        and persisted_summary["trials"] == 18
        and all(result["reward"] == 1.0 for result in adaptive_results)
        and adaptive_mean > fixed_mean
        and adaptive_mean > cold_mean
    )
    return {
        "experiment": "d2_2_useful_information_retrieval_skill",
        "training_observations": training_observations,
        "held_out_tasks": len(HELD_OUT_TASKS),
        "training_strategy_stats": training_stats,
        "held_out_results_after_restart": adaptive_results,
        "adaptive_accuracy": round(adaptive_mean, 4),
        "fixed_direct_baseline_accuracy": round(fixed_mean, 4),
        "cold_no_memory_baseline_accuracy": round(cold_mean, 4),
        "persisted_experience": persisted_summary,
        "passed": passed,
        "scope": (
            "Demonstrates exact-match information retrieval on held-out records that "
            "share the benchmark's narrow templates. It is not evidence of broad "
            "language understanding or generalization beyond these formats."
        ),
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)
