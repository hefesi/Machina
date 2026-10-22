from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.autonomy import GoalCandidate
from machina.goal_store import PersistentGoalStore


def candidate(goal_id: str = "reflect") -> GoalCandidate:
    return GoalCandidate(
        goal_id, "Reflect on progress", "reflection", .7, .8, .8, .2, .05
    )


class PersistentGoalStoreTests(unittest.TestCase):
    def test_goal_survives_restart_and_active_goal_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "goals.sqlite3"
            store = PersistentGoalStore(path)
            first = store.register(candidate())
            again = store.register(candidate())
            self.assertEqual(first["id"], again["id"])
            store.close()

            reopened = PersistentGoalStore(path)
            goals = reopened.list_goals()
            self.assertEqual(1, len(goals))
            self.assertEqual("active", goals[0]["status"])
            reopened.close()

    def test_success_completes_goal_and_future_instance_can_be_created(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            first = store.register(candidate())
            completed = store.record_outcome("reflect", "success", "Target verified")
            self.assertEqual("completed", completed["status"])
            self.assertIn("Target verified", completed["evidence"])
            second = store.register(candidate())
            self.assertNotEqual(first["id"], second["id"])
            store.close()

    def test_repeated_failures_request_revision_not_false_success(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(
                Path(directory) / "goals.sqlite3", failures_before_revision=2
            )
            store.register(candidate())
            first = store.record_outcome("reflect", "failure", "Evidence A")
            self.assertEqual("active", first["status"])
            second = store.record_outcome("reflect", "failure", "Evidence B")
            self.assertEqual("needs_revision", second["status"])
            self.assertEqual(2, second["failure_count"])
            self.assertIn("Evidence A", second["evidence"])
            self.assertIn("Evidence B", second["evidence"])
            resumed = store.resume("reflect")
            self.assertEqual("active", resumed["status"])
            store.close()

    def test_skip_pauses_goal_and_invalid_transition_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(candidate())
            paused = store.record_outcome("reflect", "skip", "Wait for more information")
            self.assertEqual("paused", paused["status"])
            with self.assertRaises(ValueError):
                store.record_outcome("reflect", "success")
            with self.assertRaises(ValueError):
                store.resume("missing")
            store.close()

    def test_status_filter_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            with self.assertRaises(ValueError):
                store.list_goals("unknown")
            self.assertEqual(0, store.summary()["total"])
            store.close()


if __name__ == "__main__":
    unittest.main()
