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


class GoalReviewerTests(unittest.TestCase):
    def test_review_is_advisory_and_apply_persists_measured_progress(self):
        from machina.goal_review import GoalReviewer

        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(GoalCandidate(
                "research", "Investigate a hypothesis", "curiosity",
                .8, .8, .8, .2, .02,
            ))
            reviewer = GoalReviewer(store)
            review = reviewer.review(
                "research",
                observed_progress=.4,
                evidence="Evaluator verified two of five milestones.",
                proposed_priority=.7,
            )
            self.assertEqual("continue", review.recommendation)
            self.assertEqual(0.0, store.list_goals()[0]["progress"])
            updated = reviewer.apply(review)
            self.assertEqual(.4, updated["progress"])
            self.assertEqual(.7, updated["priority"])
            self.assertIn("two of five", updated["evidence"])
            store.close()

    def test_regression_recommends_revision_but_does_not_transition_automatically(self):
        from machina.goal_review import GoalReviewer

        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            goal = GoalCandidate(
                "research", "Investigate a hypothesis", "curiosity",
                .8, .8, .8, .2, .02,
            )
            store.register(goal)
            store.update_progress(
                "research", .6, evidence="Initial evaluator estimate."
            )
            reviewer = GoalReviewer(store)
            review = reviewer.review(
                "research",
                observed_progress=.3,
                evidence="New evidence invalidated earlier milestones.",
            )
            self.assertEqual("revise", review.recommendation)
            self.assertEqual("active", store.list_goals()[0]["status"])
            updated = reviewer.apply(review)
            self.assertEqual(.3, updated["progress"])
            self.assertEqual("active", updated["status"])
            store.close()

    def test_explicit_failure_feedback_can_flag_goal_for_revision(self):
        from machina.goal_review import GoalReviewer

        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(
                Path(directory) / "goals.sqlite3",
                failures_before_revision=1,
            )
            store.register(GoalCandidate(
                "research", "Investigate a hypothesis", "curiosity",
                .8, .8, .8, .2, .02,
            ))
            reviewer = GoalReviewer(store)
            review = reviewer.review(
                "research",
                observed_progress=0.0,
                evidence="Independent evaluator rejected the current approach.",
            )
            updated = reviewer.apply(review, outcome="failure")
            self.assertEqual("needs_revision", updated["status"])
            self.assertEqual(1, updated["failure_count"])
            store.close()

    def test_review_rejects_missing_evidence_and_invalid_progress(self):
        from machina.goal_review import GoalReviewer

        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(GoalCandidate(
                "research", "Investigate a hypothesis", "curiosity",
                .8, .8, .8, .2, .02,
            ))
            reviewer = GoalReviewer(store)
            with self.assertRaises(ValueError):
                reviewer.review("research", observed_progress=1.2, evidence="Evidence")
            with self.assertRaises(ValueError):
                reviewer.review("research", observed_progress=.2, evidence=" ")
            store.close()


class GoalReviewConcurrencyTests(unittest.TestCase):
    def test_stale_review_cannot_overwrite_newer_evaluator_feedback(self):
        from machina.goal_review import GoalReviewer

        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            store.register(GoalCandidate(
                "research", "Investigate a hypothesis", "curiosity",
                .8, .8, .8, .2, .02,
            ))
            reviewer = GoalReviewer(store)
            stale = reviewer.review(
                "research", observed_progress=.4, evidence="First evaluation."
            )
            store.update_progress(
                "research", .6, evidence="A newer evaluation arrived."
            )
            with self.assertRaisesRegex(ValueError, "changed since review"):
                reviewer.apply(stale)
            self.assertEqual(.6, store.list_goals()[0]["progress"])
            store.close()

    def test_review_targets_its_exact_goal_record(self):
        from machina.goal_review import GoalReviewer

        with tempfile.TemporaryDirectory() as directory:
            store = PersistentGoalStore(Path(directory) / "goals.sqlite3")
            candidate = GoalCandidate(
                "research", "Investigate a hypothesis", "curiosity",
                .8, .8, .8, .2, .02,
            )
            first = store.register(candidate)
            review = GoalReviewer(store).review(
                "research", observed_progress=.3, evidence="Evidence for first."
            )
            store.record_outcome("research", "success", "First completed.")
            second = store.register(candidate)
            self.assertNotEqual(first["id"], second["id"])
            with self.assertRaises(ValueError):
                GoalReviewer(store).apply(review)
            self.assertEqual(0.0, store.list_goals()[0]["progress"])
            store.close()
