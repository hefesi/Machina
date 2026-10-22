from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.adaptive_learning import AdaptiveStrategyLearner
from examples.autonomy_adaptive_learning_demo import run_demo


class AdaptiveStrategyLearnerTests(unittest.TestCase):
    def test_unseen_strategies_are_explored_before_exploitation(self):
        with tempfile.TemporaryDirectory() as directory:
            learner = AdaptiveStrategyLearner(Path(directory) / "learn.sqlite3")
            self.assertEqual("checklist", learner.choose_strategy(
                "reasoning", ["direct", "checklist"]
            ))
            learner.record_outcome("reasoning", "checklist", 0.2)
            self.assertEqual("direct", learner.choose_strategy(
                "reasoning", ["direct", "checklist"]
            ))
            learner.close()

    def test_chooses_best_mean_reward_and_keeps_task_types_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            learner = AdaptiveStrategyLearner(Path(directory) / "learn.sqlite3")
            learner.record_outcome("math", "direct", 0.2)
            learner.record_outcome("math", "calculate", 1.0)
            self.assertEqual("calculate", learner.choose_strategy(
                "math", ["direct", "calculate"]
            ))
            self.assertEqual("calculate", learner.choose_strategy(
                "writing", ["direct", "calculate"]
            ))  # no writing data: deterministic exploration, not borrowed math data
            learner.close()

    def test_persists_learning_after_database_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "learn.sqlite3"
            learner = AdaptiveStrategyLearner(database)
            learner.record_outcome("math", "direct", 0.2)
            learner.record_outcome("math", "calculate", 1.0)
            learner.close()
            reopened = AdaptiveStrategyLearner(database)
            self.assertEqual("calculate", reopened.choose_strategy(
                "math", ["direct", "calculate"]
            ))
            self.assertEqual(2, reopened.summary()["trials"])
            reopened.close()

    def test_rejects_invalid_reward_and_empty_options(self):
        with tempfile.TemporaryDirectory() as directory:
            learner = AdaptiveStrategyLearner(Path(directory) / "learn.sqlite3")
            with self.assertRaises(ValueError):
                learner.record_outcome("math", "direct", 1.5)
            with self.assertRaises(ValueError):
                learner.choose_strategy("math", [])
            learner.close()

    def test_end_to_end_demo_beats_fixed_baseline_after_restart(self):
        result = run_demo()
        self.assertTrue(result["passed"], result)
        self.assertGreater(
            result["adaptive_mean_reward"],
            result["fixed_direct_baseline_mean_reward"],
        )
        self.assertEqual(12, result["summary"]["trials"])


if __name__ == "__main__":
    unittest.main()
