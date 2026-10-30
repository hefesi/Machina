from __future__ import annotations

import unittest

from machina.autonomy import AutonomyContext, AutonomyController, GoalCandidate
from machina.mnn_motivation import MotivationSystem, MotivationalDrive


class AutonomyControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.controller = AutonomyController()

    def test_generates_a_self_directed_goal_without_user_instruction(self):
        decision = self.controller.step(AutonomyContext(memory_count=0))
        self.assertIsNotNone(decision.selected_goal)
        self.assertEqual("establish_memory_baseline", decision.selected_goal.goal_id)
        self.assertTrue(decision.alternatives)


    def test_motivational_urgency_changes_goal_ranking(self):
        motivation = MotivationSystem([
            MotivationalDrive("curiosity", level=1.0, priority=1.0),
            MotivationalDrive("stability", level=0.0, priority=1.0),
        ])
        curiosity = GoalCandidate(
            "explore", "Explore a relevant unknown", "curiosity",
            0.5, 0.5, 0.8, 0.2, 0.05,
        )
        stability = GoalCandidate(
            "stabilize", "Inspect system stability", "stability",
            0.5, 0.5, 0.8, 0.2, 0.05,
        )
        decision = self.controller.choose(
            [stability, curiosity],
            drive_adjustments=motivation.autonomy_adjustments(),
        )
        self.assertEqual("explore", decision.selected_goal.goal_id)
        scores = {item["goal"]["goal_id"]: item["score"]["total"] for item in decision.alternatives}
        self.assertGreater(scores["explore"], scores["stabilize"])

    def test_sustained_motivational_pressure_generates_internal_goal(self):
        motivation = MotivationSystem([
            MotivationalDrive("curiosity", level=0.9, priority=1.0, persistence=0.5),
            MotivationalDrive("rest", level=0.1, priority=1.0, persistence=0.5),
        ])
        decision = self.controller.step(
            AutonomyContext(memory_count=4),
            motivation=motivation,
        )
        self.assertEqual("sustain_drive:curiosity", decision.selected_goal.goal_id)
        self.assertIn(
            "sustain_drive:curiosity",
            [item["goal"]["goal_id"] for item in decision.alternatives],
        )

    def test_motivational_goal_generation_ignores_pressure_below_threshold(self):
        motivation = MotivationSystem([
            MotivationalDrive("curiosity", level=0.1, priority=1.0),
        ])
        goals = self.controller.generate_motivational_goals(motivation)
        self.assertEqual([], goals)

    def test_motivational_goal_generation_rejects_invalid_threshold(self):
        motivation = MotivationSystem([MotivationalDrive("curiosity")])
        with self.assertRaises(ValueError):
            self.controller.generate_motivational_goals(motivation, threshold=1.1)

    def test_failed_cycle_promotes_error_recovery_goal(self):
        decision = self.controller.step(
            AutonomyContext(memory_count=4, failed_cycles=1)
        )
        self.assertEqual("analyze_recent_failure", decision.selected_goal.goal_id)

    def test_high_priority_memory_triggers_review_when_due(self):
        goals = self.controller.generate_goals(AutonomyContext(
            memory_count=5,
            important_memory_count=2,
            cycles_since_memory_review=2,
        ))
        self.assertIn("review_important_memory", [goal.goal_id for goal in goals])

    def test_external_actions_are_rejected_without_explicit_authorization(self):
        goal = GoalCandidate(
            "send_email", "Send an email", "communication",
            1.0, 1.0, 1.0, 0.0, 0.0, requires_external_action=True,
        )
        decision = self.controller.choose([goal])
        self.assertIsNone(decision.selected_goal)
        self.assertEqual("external_action_not_authorized", decision.rejected[0]["reason"])

    def test_explicitly_approved_external_candidate_can_be_considered(self):
        goal = GoalCandidate(
            "send_email", "Send an email", "communication",
            1.0, 1.0, 1.0, 0.0, 0.0, requires_external_action=True,
        )
        decision = self.controller.choose([goal], approved_external_goal_ids=["send_email"])
        self.assertEqual("send_email", decision.selected_goal.goal_id)

    def test_risky_goal_is_rejected_and_rationale_is_inspectable(self):
        risky = GoalCandidate(
            "delete_data", "Delete data", "cleanup",
            1.0, 0.9, 0.9, 0.1, 0.9,
        )
        safe = GoalCandidate(
            "inspect", "Inspect state", "monitoring",
            0.4, 0.4, 0.9, 0.1, 0.01,
        )
        decision = self.controller.choose([risky, safe])
        self.assertEqual("inspect", decision.selected_goal.goal_id)
        self.assertEqual("risk_above_limit", decision.rejected[0]["reason"])
        self.assertIn("total", decision.alternatives[0]["score"])

    def test_duplicate_ids_and_invalid_context_are_rejected(self):
        goal = GoalCandidate("same", "First", "test", .2, .2, .2, .2, .2)
        duplicate = GoalCandidate("same", "Second", "test", .3, .3, .3, .3, .3)
        with self.assertRaises(ValueError):
            self.controller.choose([goal, duplicate])
        with self.assertRaises(ValueError):
            AutonomyContext(memory_count=-1)


if __name__ == "__main__":
    unittest.main()
