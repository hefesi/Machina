from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.planning import HierarchicalPlanner, PersistentPlanStore


class HierarchicalPlannerTests(unittest.TestCase):
    def goal(self, status: str = "active") -> dict:
        return {
            "id": 4,
            "goal_id": "investigate_open_questions",
            "description": "Investigate unresolved questions",
            "status": status,
        }

    def test_decomposition_creates_ordered_steps_and_dependencies(self):
        steps = HierarchicalPlanner().decompose(
            "investigate_open_questions", "Investigate unresolved questions"
        )
        self.assertEqual(4, len(steps))
        self.assertEqual([], steps[0]["dependencies"])
        self.assertEqual([steps[0]["step_id"]], steps[1]["dependencies"])
        self.assertEqual([steps[1]["step_id"]], steps[2]["dependencies"])
        self.assertEqual([1, 2, 3, 4], [step["order"] for step in steps])

    def test_ready_steps_advance_only_after_dependencies_are_evaluated(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentPlanStore(Path(directory) / "plans.sqlite3")
            plan = store.create_plan(self.goal())
            ready = store.ready_steps(plan["id"])
            self.assertEqual([plan["steps"][0]["step_id"]], [step["step_id"] for step in ready])
            with self.assertRaises(ValueError):
                store.record_step_outcome(plan["id"], plan["steps"][1]["step_id"], "success")
            updated = store.record_step_outcome(
                plan["id"], plan["steps"][0]["step_id"], "success", "Criterion met"
            )
            self.assertEqual("completed", updated["steps"][0]["status"])
            self.assertEqual(plan["steps"][1]["step_id"], store.ready_steps(plan["id"])[0]["step_id"])
            store.close()

    def test_failure_requires_revision_and_resume_preserves_completed_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plans.sqlite3"
            store = PersistentPlanStore(path)
            plan = store.create_plan(self.goal())
            first_id = plan["steps"][0]["step_id"]
            store.record_step_outcome(plan["id"], first_id, "success", "done")
            second_id = store.ready_steps(plan["id"])[0]["step_id"]
            failed = store.record_step_outcome(plan["id"], second_id, "failure", "missing evidence")
            self.assertEqual("needs_revision", failed["status"])
            self.assertEqual("needs_revision", failed["steps"][1]["status"])
            resumed = store.resume_plan(plan["id"])
            self.assertEqual("active", resumed["status"])
            self.assertEqual("completed", resumed["steps"][0]["status"])
            self.assertEqual("pending", resumed["steps"][1]["status"])
            self.assertEqual(second_id, store.ready_steps(plan["id"])[0]["step_id"])
            store.close()

            reopened = PersistentPlanStore(path)
            self.assertEqual("active", reopened.get_plan(plan["id"])["status"])
            reopened.close()

    def test_skip_pauses_plan_and_allows_resume(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentPlanStore(Path(directory) / "plans.sqlite3")
            plan = store.create_plan(self.goal())
            step_id = plan["steps"][0]["step_id"]
            paused = store.record_step_outcome(plan["id"], step_id, "skip", "waiting for data")
            self.assertEqual("paused", paused["status"])
            self.assertEqual([], store.ready_steps(plan["id"]))
            resumed = store.resume_plan(plan["id"])
            self.assertEqual("active", resumed["status"])
            self.assertEqual("pending", resumed["steps"][0]["status"])
            store.close()

    def test_only_open_goals_can_be_planned_and_active_plan_is_reused(self):
        with tempfile.TemporaryDirectory() as directory:
            store = PersistentPlanStore(Path(directory) / "plans.sqlite3")
            first = store.create_plan(self.goal())
            again = store.create_plan(self.goal())
            self.assertEqual(first["id"], again["id"])
            with self.assertRaises(ValueError):
                store.create_plan(self.goal("completed"))
            with self.assertRaises(ValueError):
                store.get_plan(999)
            store.close()


if __name__ == "__main__":
    unittest.main()
