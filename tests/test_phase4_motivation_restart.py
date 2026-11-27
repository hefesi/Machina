from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import (
    AutonomyContext,
    AutonomyController,
    HomeostaticProposal,
    InternalDeliberator,
    MotivationSystem,
    MotivationalDrive,
    PersistentGoalStore,
    VirtualBrain,
)
from machina.curiosity_coordination import CuriosityGoalCoordinator
from machina.goal_outcome_learning import GoalOutcomeLearner
from machina.self_model import SelfModel
from machina.self_model_learning import SelfModelLearningBridge


class Phase4MotivationRestartTests(unittest.TestCase):
    def test_latest_feedback_snapshot_is_restored_before_next_curiosity_decision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brain_path = root / "brain.sqlite"
            goals_path = root / "goals.sqlite"
            outcomes_path = root / "outcomes.sqlite"
            curiosity_path = root / "curiosity.sqlite"

            mappings = {
                "memory_gap": {
                    "question": "Which evidence explains the memory gap?",
                    "drive": "memory",
                    "hypothesis": "A missing retrieval relation may explain the gap.",
                    "information_gain": 0.9,
                    "impact": 0.8,
                    "urgency": 0.8,
                    "estimated_cost": 0.1,
                    "risk": 0.02,
                },
                "curiosity_gap": {
                    "question": "Which evidence explains the curiosity gap?",
                    "drive": "curiosity",
                    "hypothesis": "A missing knowledge relation may explain the gap.",
                    "information_gain": 0.9,
                    "impact": 0.8,
                    "urgency": 0.8,
                    "estimated_cost": 0.1,
                    "risk": 0.02,
                },
            }

            def make_motivation() -> MotivationSystem:
                return MotivationSystem(drives=[
                    MotivationalDrive(
                        "memory", level=0.9, setpoint=0.1,
                        recovery_rate=0.0, relief_gain=0.8, pressure=0.9,
                    ),
                    MotivationalDrive(
                        "curiosity", level=0.5, setpoint=0.5,
                        recovery_rate=0.0, relief_gain=0.0, pressure=0.5,
                    ),
                ])

            def build_brain():
                controller = AutonomyController()
                goals = PersistentGoalStore(goals_path)
                learner = GoalOutcomeLearner(outcomes_path)
                coordinator = CuriosityGoalCoordinator(
                    SelfModelLearningBridge(SelfModel(), learner), controller
                )
                brain = VirtualBrain(
                    brain_path,
                    internal_deliberator=InternalDeliberator(controller, goals),
                    curiosity_investigation_path=curiosity_path,
                    motivation_system=make_motivation(),
                    curiosity_goal_coordinator=coordinator,
                )
                return brain, goals, learner

            first_brain, first_goals, first_learner = build_brain()
            try:
                first = first_brain.run_deliberated_cycle(
                    "Compare two evidence-backed knowledge gaps.",
                    AutonomyContext(memory_count=1),
                    motivational_fulfillment={"memory": 1.0},
                    curiosity_gap_mappings=mappings,
                    cycle_id="phase4-motivation-cycle-1",
                )
                first_trace = next(
                    event.artifact for event in first.events
                    if event.event_type == "goal.deliberated"
                )
                first_curiosity = first_trace.data["curiosity_context"]
                self.assertEqual("curiosity", first_trace.data["selected_source"])
                self.assertEqual(
                    "investigate_gap:memory-gap",
                    first_curiosity["candidate_goal_id"],
                )
                self.assertTrue(first_curiosity["selected_by_unified_deliberation"])
                first_memory_score = next(
                    item["score"] for item in first_curiosity["selector_decision"]["ranked"]
                    if item["question"]["question_id"] == "investigate_gap:memory-gap"
                )
                self.assertAlmostEqual(0.12, first_memory_score["drive_adjustment"])
                self.assertEqual(1, first_brain.motivation_system.timestep)
                self.assertAlmostEqual(
                    0.1, first_brain.motivation_system.drives["memory"].level
                )
                self.assertAlmostEqual(
                    0.1, first_brain.motivation_system.drives["memory"].pressure
                )
                first_goals.record_outcome(
                    "investigate_gap:memory-gap",
                    "success",
                    evidence="The controlled test evaluator confirms this focus is complete.",
                )
                self.assertTrue(first_brain.audit_cycle(first.cycle_id).valid)
            finally:
                first_brain.close()
                first_learner.close()
                first_goals.close()

            second_brain, second_goals, second_learner = build_brain()
            try:
                # The constructor must restore the last committed motivation
                # snapshot before this process performs another selection.
                self.assertEqual(1, second_brain.motivation_system.timestep)
                self.assertAlmostEqual(
                    0.1, second_brain.motivation_system.drives["memory"].level
                )
                self.assertAlmostEqual(
                    0.1, second_brain.motivation_system.drives["memory"].pressure
                )
                self.assertAlmostEqual(
                    -0.12,
                    second_brain.motivation_system.temporal_autonomy_adjustments()["memory"],
                )

                proposal = HomeostaticProposal(
                    cycle_id="phase4-motivation-cycle-2",
                    adjustments={"curiosity": -0.02},
                    deviations={"runtime_stability": 0.3},
                    persistence={"runtime_stability": 3},
                    evidence_refs=("telemetry:phase4-cycle-2",),
                    rationale=("A sustained deviation temporarily limits exploration.",),
                )
                second = second_brain.run_deliberated_cycle(
                    "Continue with the remaining evidence-backed knowledge gap.",
                    AutonomyContext(memory_count=1),
                    homeostatic_proposal=proposal,
                    curiosity_gap_mappings=mappings,
                    cycle_id="phase4-motivation-cycle-2",
                )
                second_trace = next(
                    event.artifact for event in second.events
                    if event.event_type == "goal.deliberated"
                )
                second_curiosity = second_trace.data["curiosity_context"]
                self.assertEqual("curiosity", second_trace.data["selected_source"])
                self.assertEqual(
                    "investigate_gap:curiosity-gap",
                    second_curiosity["candidate_goal_id"],
                )
                self.assertTrue(second_curiosity["selected_by_unified_deliberation"])
                self.assertEqual("homeostasis", second_curiosity["stability_pressure_source"])
                self.assertAlmostEqual(0.3, second_curiosity["stability_pressure"])
                curiosity_score = next(
                    item["score"] for item in second_curiosity["selector_decision"]["ranked"]
                    if item["question"]["question_id"] == "investigate_gap:curiosity-gap"
                )
                self.assertAlmostEqual(-0.02, curiosity_score["drive_adjustment"])
                autonomy_score = next(
                    item["score"] for item in second_trace.data["deliberation"]["autonomy"]["alternatives"]
                    if item["goal"]["goal_id"] == "investigate_gap:curiosity-gap"
                )
                self.assertAlmostEqual(-0.02, autonomy_score["feedback_adjustment"])

                feedback = next(
                    event.artifact for event in second.events
                    if event.event_type == "motivation.feedback_applied"
                )
                self.assertEqual(1, feedback.data["previous_timestep"])
                self.assertEqual(2, feedback.data["timestep"])
                self.assertEqual(2, second_brain.motivation_system.timestep)
                self.assertEqual(2, len(second_brain.curiosity_store.history()))
                self.assertTrue(second_brain.audit_cycle(second.cycle_id).valid)
            finally:
                second_brain.close()
                second_learner.close()
                second_goals.close()


if __name__ == "__main__":
    unittest.main()
