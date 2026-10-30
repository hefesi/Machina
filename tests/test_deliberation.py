from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.autonomy import AutonomyContext, AutonomyController, GoalCandidate
from machina.deliberation import InternalDeliberator
from machina.goal_store import PersistentGoalStore


class InternalDeliberatorTests(unittest.TestCase):
    def test_selects_and_persists_generated_goal_with_rationale(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            deliberator = InternalDeliberator(AutonomyController(), store)
            result = deliberator.deliberate(
                AutonomyContext(unresolved_questions=3, cycles_since_reflection=4)
            )
            self.assertIsNotNone(result.selected_goal)
            self.assertEqual("generated", result.selected_source)
            self.assertIsNotNone(result.persistent_record_id)
            self.assertEqual(1, result.cycle)
            self.assertTrue(result.rationale)
            self.assertEqual(1, len(store.list_goals(status="active")))
            store.close()

    def test_reuses_persistent_goal_instead_of_creating_duplicate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            goal = GoalCandidate(
                "investigate_open_questions", "Existing investigation",
                "curiosity", .9, .8, .8, .2, .05,
            )
            original = store.register(goal)
            store.update_progress(
                goal.goal_id, .25, priority=.95, evidence="Investigation started"
            )
            deliberator = InternalDeliberator(AutonomyController(), store)
            result = deliberator.deliberate(AutonomyContext(unresolved_questions=2))
            self.assertEqual("persistent", result.selected_source)
            self.assertEqual(original["id"], result.persistent_record_id)
            self.assertEqual(1, len(store.list_goals(status="active")))
            store.close()

    def test_does_not_mutate_goal_lifecycle_or_execute_external_actions(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(GoalCandidate(
                "existing", "Existing", "maintenance", .8, .8, .8, .2, .02
            ))
            deliberator = InternalDeliberator(AutonomyController(), store)
            deliberator.deliberate(AutonomyContext())
            self.assertEqual(1, len(store.list_goals(status="active")))
            self.assertEqual(0, store.summary()["completed"])
            store.close()

    def test_open_goal_limit_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            deliberator = InternalDeliberator(AutonomyController(), store)
            with self.assertRaises(ValueError):
                deliberator.deliberate(AutonomyContext(), open_goal_limit=0)
            store.close()


    def test_deliberation_history_survives_restart_and_informs_next_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "goals.sqlite3"
            first_store = PersistentGoalStore(path)
            first_deliberator = InternalDeliberator(AutonomyController(), first_store)
            first = first_deliberator.deliberate(
                AutonomyContext(unresolved_questions=3, cycles_since_reflection=4)
            )
            self.assertIsNotNone(first.history_record_id)
            self.assertIsNone(first.previous_goal_id)
            first_store.close()

            reopened_store = PersistentGoalStore(path)
            second_deliberator = InternalDeliberator(AutonomyController(), reopened_store)
            second = second_deliberator.deliberate(
                AutonomyContext(unresolved_questions=3, cycles_since_reflection=4)
            )
            self.assertEqual(first.selected_goal.goal_id, second.previous_goal_id)
            history = reopened_store.recent_deliberations(5)
            self.assertEqual(2, len(history))
            self.assertEqual(first.selected_goal.goal_id, history[1]["selected_goal_id"])
            self.assertEqual(second.selected_goal.goal_id, history[0]["selected_goal_id"])
            self.assertTrue(history[0]["alternatives"])
            reopened_store.close()

    def test_deliberation_history_validates_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            with self.assertRaises(ValueError):
                store.recent_deliberations(0)
            store.close()



if __name__ == "__main__":
    unittest.main()
