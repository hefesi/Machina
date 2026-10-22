from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.adaptive_learning import AdaptiveStrategyLearner
from machina.skill_benchmark import RetrievalTask, score, solve
from examples.autonomy_d22_useful_skill_demo import (
    HELD_OUT_TASKS,
    STRATEGIES,
    run_demo,
)


class UsefulSkillTests(unittest.TestCase):
    def test_decomposition_retrieves_target_fact_not_first_fact(self):
        task = RetrievalTask(
            "prose_lookup",
            "Nora's editor is Vim. Ivo's editor is Helix.",
            "What is the editor for Ivo?",
            "Helix",
        )
        self.assertEqual("Vim", solve(task, "direct"))
        self.assertEqual("Helix", solve(task, "decompose"))
        self.assertEqual(1.0, score(task, "decompose"))

    def test_checklist_retrieves_matching_structured_row(self):
        task = RetrievalTask(
            "table_lookup",
            "entity | field | value\nAri | room | 3\nBea | room | 19",
            "What is the room for Bea?",
            "19",
        )
        self.assertEqual("3", solve(task, "direct"))
        self.assertEqual("19", solve(task, "checklist"))
        self.assertEqual(1.0, score(task, "checklist"))

    def test_rejects_unsupported_question_format_and_strategy(self):
        task = RetrievalTask("prose_lookup", "Ari's room is 3.", "Tell me Ari's room.", "3")
        with self.assertRaises(ValueError):
            solve(task, "decompose")
        valid = RetrievalTask(
            "prose_lookup", "Ari's room is 3.", "What is the room for Ari?", "3"
        )
        with self.assertRaises(ValueError):
            solve(valid, "magic")

    def test_persistent_strategy_selection_uses_task_specific_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "learner.sqlite3"
            learner = AdaptiveStrategyLearner(database)
            learner.record_outcome("prose_lookup", "direct", 0.0)
            learner.record_outcome("prose_lookup", "decompose", 1.0)
            learner.record_outcome("table_lookup", "direct", 0.0)
            learner.record_outcome("table_lookup", "checklist", 1.0)
            learner.close()

            learner = AdaptiveStrategyLearner(database)
            self.assertEqual("decompose", learner.choose_strategy(
                "prose_lookup", STRATEGIES
            ))
            self.assertEqual("checklist", learner.choose_strategy(
                "table_lookup", STRATEGIES
            ))
            learner.close()

    def test_end_to_end_held_out_skill_beats_both_controls_after_restart(self):
        result = run_demo()
        self.assertTrue(result["passed"], result)
        self.assertEqual(1.0, result["adaptive_accuracy"])
        self.assertGreater(
            result["adaptive_accuracy"], result["fixed_direct_baseline_accuracy"]
        )
        self.assertGreater(
            result["adaptive_accuracy"], result["cold_no_memory_baseline_accuracy"]
        )
        self.assertEqual(18, result["persisted_experience"]["trials"])
        self.assertEqual(4, len(HELD_OUT_TASKS))


if __name__ == "__main__":
    unittest.main()
