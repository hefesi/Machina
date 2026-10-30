import tempfile
import unittest
from pathlib import Path

from machina.autonomy import GoalCandidate
from machina.goal_store import PersistentGoalStore
from machina.goal_constraints import GoalConflictResolver


class GoalConstraintTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = PersistentGoalStore(Path(self.tmp.name) / "goals.sqlite3")
        self.resolver = GoalConflictResolver(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_conflicts_are_symmetric_and_persisted(self):
        relation = self.store.add_goal_relation(
            "research", "deploy", "conflicts", strength=.9,
            evidence="Both require exclusive control of the same test environment.",
        )
        assessment = self.resolver.assess(["deploy", "research"])
        self.assertFalse(assessment.compatible)
        self.assertEqual("prioritize_one", assessment.recommendation)
        self.assertEqual(("deploy", "research"), (
            relation["source_goal_id"], relation["target_goal_id"]
        ))
        self.assertEqual(1, len(assessment.conflicts))
        self.assertEqual(1, len(self.store.goal_relations("research")))

    def test_resource_budget_and_dependency_are_explained(self):
        self.store.add_goal_relation(
            "publish", "review", "requires",
            evidence="Publication requires completed review.",
        )
        missing = self.resolver.assess(["publish"])
        self.assertEqual("needs_dependency", missing.recommendation)
        self.assertEqual("review", missing.missing_requirements[0]["target_goal_id"])

        budget = self.resolver.assess(
            ["publish", "review"],
            resource_costs={"publish": {"compute": 4}, "review": {"compute": 3}},
            resource_limits={"compute": 5},
        )
        self.assertFalse(budget.compatible)
        self.assertEqual("defer_or_reallocate", budget.recommendation)
        self.assertEqual(7.0, budget.resource_totals["compute"])

    def test_compatible_goals_can_be_co_selected(self):
        result = self.resolver.assess(
            ["learn", "document"],
            resource_costs={"learn": {"time": 2}, "document": {"time": 1}},
            resource_limits={"time": 4},
        )
        self.assertTrue(result.compatible)
        self.assertEqual("co_select", result.recommendation)

    def test_invalid_relations_and_costs_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.add_goal_relation(
                "same", "same", "conflicts", evidence="Invalid self relation."
            )
        with self.assertRaises(ValueError):
            self.store.add_goal_relation(
                "a", "b", "conflicts", evidence=" "
            )
        with self.assertRaises(ValueError):
            self.resolver.assess(
                ["a"], resource_costs={"a": {"cpu": -1}}
            )

    def test_assessment_does_not_change_goal_lifecycle(self):
        self.store.register(GoalCandidate(
            "a", "Goal A", "curiosity", .8, .8, .8, .2, .02
        ))
        self.store.register(GoalCandidate(
            "b", "Goal B", "curiosity", .8, .8, .8, .2, .02
        ))
        self.store.add_goal_relation(
            "a", "b", "conflicts", evidence="Competing test fixture."
        )
        self.resolver.assess(["a", "b"])
        self.assertEqual(2, len(self.store.list_goals(status="active")))


if __name__ == "__main__":
    unittest.main()
