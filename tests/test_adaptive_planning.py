import tempfile
import unittest
from pathlib import Path

from machina.adaptive_planning import AdaptivePlanReviewer
from machina.goal_constraints import GoalConflictResolver
from machina.goal_store import PersistentGoalStore


class AdaptivePlanningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "goals.sqlite3"
        self.store = PersistentGoalStore(self.path)
        self.resolver = GoalConflictResolver(self.store)
        self.reviewer = AdaptivePlanReviewer(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_plan_change_is_explained_and_persisted(self):
        first = self.resolver.schedule(
            ["research", "deploy"], utilities={"research": .9, "deploy": .3}
        )
        self.reviewer.review([], first, trigger="initial planning")
        second = self.resolver.schedule(
            ["research", "deploy"], utilities={"research": .2, "deploy": .95}
        )
        revision = self.reviewer.review(
            first.selected_goal_ids, second,
            trigger="new evidence changed expected benefit",
            context={"environment_version": 2},
        )
        self.assertEqual(("research",), revision.newly_deferred_goal_ids)
        self.assertEqual(("deploy",), revision.newly_selected_goal_ids)
        self.assertIn("novos objetivos selecionados", revision.rationale)
        history = self.store.recent_plan_revisions()
        self.assertEqual(2, len(history))
        self.assertEqual("new evidence changed expected benefit", history[0]["trigger"])
        self.assertEqual({"environment_version": 2}, history[0]["context"])

    def test_deferred_goal_can_be_recognized_as_restored(self):
        first = self.resolver.schedule(
            ["a", "b"], utilities={"a": .9, "b": .1}
        )
        self.reviewer.review([], first, trigger="initial")
        second = self.resolver.schedule(
            ["a", "b"], utilities={"a": .1, "b": .9}
        )
        self.reviewer.review(first.selected_goal_ids, second, trigger="priority shift")
        third = self.resolver.schedule(
            ["a", "b"], utilities={"a": .9, "b": .1}
        )
        revision = self.reviewer.review(
            second.selected_goal_ids, third, trigger="new evidence favors a"
        )
        self.assertEqual(("a",), revision.restored_goal_ids)

    def test_revision_history_survives_store_restart(self):
        schedule = self.resolver.schedule(["a"], utilities={"a": .8})
        self.reviewer.review([], schedule, trigger="startup")
        self.store.close()
        self.store = PersistentGoalStore(self.path)
        self.assertEqual("startup", self.store.recent_plan_revisions()[0]["trigger"])

    def test_invalid_review_inputs_are_rejected(self):
        schedule = self.resolver.schedule(["a"])
        with self.assertRaises(ValueError):
            self.reviewer.review(["a", "a"], schedule, trigger="bad")
        with self.assertRaises(ValueError):
            self.reviewer.review([], schedule, trigger=" ")

if __name__ == "__main__":
    unittest.main()
