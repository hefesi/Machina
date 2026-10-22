from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.adaptive_learning import AdaptiveStrategyLearner
from machina.skill_benchmark import score
from machina.transfer_benchmark import TRANSFER_TASKS, score_transfer, solve_transfer
from examples.autonomy_d22_useful_skill_demo import STRATEGIES, TRAINING_TASKS
from examples.autonomy_d24_generalization_transfer_demo import run_demo


class GeneralizationTransferTests(unittest.TestCase):
    def test_decompose_transfers_to_unseen_bullet_format(self):
        task = TRANSFER_TASKS[0]
        self.assertEqual("Vim", solve_transfer(task, "direct"))
        self.assertEqual("Helix", solve_transfer(task, "decompose"))
        self.assertEqual(1.0, score_transfer(task, "decompose"))

    def test_decompose_transfers_to_unseen_record_format(self):
        task = TRANSFER_TASKS[2]
        self.assertNotEqual(task.expected_answer, solve_transfer(task, "direct"))
        self.assertEqual("Zed", solve_transfer(task, "decompose"))
        self.assertEqual(1.0, score_transfer(task, "decompose"))

    def test_unseen_task_type_uses_global_experience_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "transfer.sqlite3"
            learner = AdaptiveStrategyLearner(database)
            for task in TRAINING_TASKS:
                for strategy in STRATEGIES:
                    learner.record_outcome(
                        task.task_type, strategy, score(task, strategy)
                    )
            learner.close()

            learner = AdaptiveStrategyLearner(database)
            self.assertEqual(
                "decompose",
                learner.choose_strategy("unseen_bullet_format", STRATEGIES),
            )
            self.assertEqual(
                "decompose",
                learner.choose_strategy("unseen_record_format", STRATEGIES),
            )
            learner.close()

    def test_end_to_end_transfer_beats_baselines(self):
        result = run_demo()
        self.assertTrue(result["passed"], result)
        self.assertEqual(1.0, result["adaptive_transfer_accuracy"])
        self.assertGreater(
            result["adaptive_transfer_accuracy"],
            result["fixed_direct_baseline_accuracy"],
        )
        self.assertGreater(
            result["adaptive_transfer_accuracy"],
            result["cold_no_memory_baseline_accuracy"],
        )
        self.assertEqual(18, result["persisted_experience"]["trials"])
        self.assertEqual(4, len(TRANSFER_TASKS))


if __name__ == "__main__":
    unittest.main()
