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

    def test_abandon_requires_reason_and_preserves_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(candidate())
            abandoned = store.abandon("reflect", "Repeatedly not useful")
            self.assertEqual("abandoned", abandoned["status"])
            self.assertIn("ABANDONED: Repeatedly not useful", abandoned["evidence"])
            with self.assertRaises(ValueError):
                store.abandon("reflect", "again")
            with self.assertRaises(ValueError):
                store.abandon("missing", "")
            store.close()

    def test_status_filter_is_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            with self.assertRaises(ValueError):
                store.list_goals("unknown")
            self.assertEqual(0, store.summary()["total"])
            store.close()


    def test_progress_and_priority_are_explicit_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "goals.sqlite3"
            store = PersistentGoalStore(path)
            store.register(candidate())
            updated = store.update_progress(
                "reflect", 0.4, priority=0.9, evidence="Two of five checks passed"
            )
            self.assertEqual(0.4, updated["progress"])
            self.assertEqual(0.9, updated["priority"])
            store.close()

            reopened = PersistentGoalStore(path)
            restored = reopened.list_goals()[0]
            self.assertEqual(0.4, restored["progress"])
            self.assertEqual(0.9, restored["priority"])
            self.assertIn("Two of five checks passed", restored["evidence"])
            reopened.close()

    def test_progress_requires_valid_value_and_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(candidate())
            for value in (-0.1, 1.1, float("nan"), True):
                with self.assertRaises(ValueError):
                    store.update_progress("reflect", value, evidence="measurement")
            with self.assertRaises(ValueError):
                store.update_progress("reflect", 0.5, evidence=" ")
            with self.assertRaises(ValueError):
                store.update_progress("reflect", 0.5, priority=1.1, evidence="measurement")
            store.close()

    def test_progress_can_be_revised_when_new_evidence_changes_estimate(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(candidate())
            store.update_progress("reflect", 0.7, evidence="Initial estimate")
            revised = store.update_progress("reflect", 0.3, evidence="A prior result was invalidated")
            self.assertEqual(0.3, revised["progress"])
            self.assertIn("Initial estimate", revised["evidence"])
            self.assertIn("invalidated", revised["evidence"])
            store.close()


    def test_ranked_open_goals_use_priority_and_keep_paused_goals_out(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(candidate("low"))
            store.register(GoalCandidate("high", "High priority", "curiosity", .8, .9, .8, .2, .05))
            store.update_progress("low", 0.2, priority=0.3, evidence="low priority")
            store.update_progress("high", 0.1, priority=0.9, evidence="high priority")
            store.record_outcome("low", "skip", "Pause pending information")
            ranked = store.ranked_open_goals()
            self.assertEqual(["high"], [goal["goal_id"] for goal in ranked])
            store.resume("low")
            ranked = store.ranked_open_goals()
            self.assertEqual(["high", "low"], [goal["goal_id"] for goal in ranked])
            store.close()

    def test_ranked_open_goals_validates_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            for invalid in (0, -1, True, 1.5):
                with self.assertRaises(ValueError):
                    store.ranked_open_goals(invalid)
            store.close()


if __name__ == "__main__":
    unittest.main()
