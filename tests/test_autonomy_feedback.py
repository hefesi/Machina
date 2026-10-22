from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.autonomy import (
    AutonomyExperienceStore,
    AutonomyController,
    GoalCandidate,
)


class AutonomyFeedbackTests(unittest.TestCase):
    def test_feedback_persists_and_changes_drive_adjustment(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "autonomy.sqlite3"
            store = AutonomyExperienceStore(path)
            goal = GoalCandidate(
                "inspect", "Inspect state", "self_monitoring", .2, .3, .9, .1, .01
            )
            store.record_selection(goal)
            result = store.record_feedback("success")
            self.assertEqual("success", result["outcome"])
            store.close()

            reopened = AutonomyExperienceStore(path)
            self.assertEqual(1, reopened.summary()["successes"])
            self.assertGreater(reopened.drive_adjustments()["self_monitoring"], 0)
            reopened.close()

    def test_feedback_requires_pending_goal_and_valid_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            store = AutonomyExperienceStore(Path(directory) / "autonomy.sqlite3")
            with self.assertRaises(ValueError):
                store.record_feedback("success")
            with self.assertRaises(ValueError):
                store.record_feedback("maybe")
            store.close()

    def test_repetition_penalty_is_visible_and_changes_selection(self):
        controller = AutonomyController()
        first = GoalCandidate("a", "Goal A", "alpha", .5, .5, .5, .1, .05)
        second = GoalCandidate("b", "Goal B", "beta", .5, .5, .5, .1, .05)
        decision = controller.choose(
            [first, second],
            drive_adjustments={"beta": 0.05},
            recent_goal_ids=["b"],
        )
        self.assertEqual("a", decision.selected_goal.goal_id)
        self.assertEqual(-0.08, decision.alternatives[1]["score"]["repetition_penalty"])


if __name__ == "__main__":
    unittest.main()
