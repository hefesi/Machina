from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.adaptive_learning import AdaptiveStrategyLearner
from machina.continuous_learning import learn_batch
from machina.skill_benchmark import score
from examples.autonomy_d22_useful_skill_demo import STRATEGIES, TRAINING_TASKS
from examples.autonomy_d23_continuous_learning_demo import run_demo


class ContinuousLearningTests(unittest.TestCase):
    def test_experience_is_persisted_incrementally_across_restarts(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "incremental.sqlite3"
            learner = AdaptiveStrategyLearner(database)
            task = next(task for task in TRAINING_TASKS if task.task_type == "prose_lookup")
            self.assertEqual(3, learn_batch(learner, [task], STRATEGIES, score))
            learner.close()
            learner = AdaptiveStrategyLearner(database)
            self.assertEqual(3, learner.summary()["trials"])
            self.assertEqual(1.0, learner.strategy_stats("prose_lookup")["decompose"]["mean_reward"])
            learner.close()

    def test_learning_a_later_family_does_not_erase_earlier_family(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "retention.sqlite3"
            learner = AdaptiveStrategyLearner(database)
            prose = [task for task in TRAINING_TASKS if task.task_type == "prose_lookup"]
            table = [task for task in TRAINING_TASKS if task.task_type == "table_lookup"]
            learn_batch(learner, prose, STRATEGIES, score)
            before = learner.strategy_stats("prose_lookup")
            learner.close()
            learner = AdaptiveStrategyLearner(database)
            learn_batch(learner, table, STRATEGIES, score)
            learner.close()
            learner = AdaptiveStrategyLearner(database)
            self.assertEqual(before, learner.strategy_stats("prose_lookup"))
            self.assertEqual(1.0, learner.strategy_stats("table_lookup")["checklist"]["mean_reward"])
            learner.close()

    def test_end_to_end_continuous_learning_demo(self):
        result = run_demo()
        self.assertTrue(result["passed"], result)
        self.assertEqual(18, result["persisted_experience_after_two_restarts"]["trials"])
        self.assertEqual(1.0, result["held_out_accuracy"])
        self.assertEqual(result["prose_strategy_stats_before_later_learning"], result["prose_strategy_stats_after_later_learning_and_restart"])


if __name__ == "__main__":
    unittest.main()
