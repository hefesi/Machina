import tempfile
import unittest
from pathlib import Path

from machina.autonomy import AutonomyContext, AutonomyController
from machina.curiosity import CuriosityInvestigationStore
from machina.curiosity_coordination import CuriosityGoalCoordinator
from machina.goal_outcome_learning import GoalOutcomeLearner
from machina.homeostasis import HomeostaticProposal
from machina.mnn_motivation import MotivationSystem, MotivationalDrive
from machina.self_model import SelfModel
from machina.self_model_learning import SelfModelLearningBridge


class CuriosityGoalCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.model = SelfModel()
        self.learner = GoalOutcomeLearner(Path(self.tmp.name) / "outcomes.sqlite3")
        self.bridge = SelfModelLearningBridge(self.model, self.learner)
        self.controller = AutonomyController()
        self.coordinator = CuriosityGoalCoordinator(self.bridge, self.controller)
        self.store = CuriosityInvestigationStore(Path(self.tmp.name) / "curiosity.sqlite3")

    def tearDown(self):
        self.store.close()
        self.learner.close()
        self.tmp.cleanup()

    def mappings(self):
        return {
            "memory_gap": {
                "question": "Which evidence explains the memory gap?",
                "hypothesis": "A missing retrieval relation may explain the gap.",
                "information_gain": 0.9,
                "impact": 0.9,
                "urgency": 0.8,
                "estimated_cost": 0.1,
                "risk": 0.02,
            }
        }

    def test_curiosity_selection_is_integrated_and_persisted_only_after_autonomy(self):
        result = self.coordinator.deliberate(
            self.mappings(),
            cycle_id="cycle-1",
            investigation_store=self.store,
        )
        self.assertEqual("investigate_gap:memory-gap", result["selected_goal_id"])
        self.assertTrue(result["curiosity_goal_selected"])
        self.assertEqual("open", result["investigation"]["status"])
        self.assertEqual("A missing retrieval relation may explain the gap.", result["investigation"]["hypothesis"])
        self.assertFalse(result["execution_performed"])
        self.assertEqual(1, len(self.store.open_investigations()))

    def test_homeostatic_pressure_reduces_exploration_and_adjustments_reach_autonomy(self):
        proposal = HomeostaticProposal(
            cycle_id="cycle-1",
            adjustments={"curiosity": 0.1},
            deviations={"prediction_error": 0.6},
            persistence={"prediction_error": 3},
            evidence_refs=("telemetry:cycle-1",),
            rationale=("prediction_error remained outside its range",),
        )
        motivation = MotivationSystem([
            MotivationalDrive("curiosity", level=1.0, setpoint=0.5),
        ])
        result = self.coordinator.deliberate(
            self.mappings(),
            cycle_id="cycle-1",
            investigation_store=self.store,
            homeostatic_proposal=proposal,
            motivation=motivation,
        )
        self.assertAlmostEqual(0.6, result["stability_pressure"])
        self.assertEqual("homeostasis", result["stability_pressure_source"])
        self.assertAlmostEqual(0.25, result["drive_adjustments"]["curiosity"])
        curiosity_score = result["curiosity_decision"].ranked[0]["score"]
        self.assertAlmostEqual(0.55, curiosity_score["uncertainty_information_gain"] / (
            0.34 * result["curiosity_decision"].exploration_weight
        ))
        autonomy_score = result["autonomy_decision"].alternatives[0]["score"]
        self.assertAlmostEqual(0.25, autonomy_score["feedback_adjustment"])

    def test_persisted_question_is_suppressed_on_later_cycles(self):
        first = self.coordinator.deliberate(
            self.mappings(), cycle_id="cycle-1", investigation_store=self.store,
        )
        self.assertIsNotNone(first["investigation"])
        second = self.coordinator.deliberate(
            self.mappings(), cycle_id="cycle-2", investigation_store=self.store,
        )
        self.assertIsNone(second["curiosity_candidate_goal_id"])
        self.assertIsNone(second["investigation"])
        self.assertEqual("prior_investigation_exists", second["proposals"]["suppressed"][0]["reason"])

    def test_no_investigation_is_persisted_when_another_goal_wins(self):
        low_value = self.mappings()
        low_value["memory_gap"].update({
            "information_gain": 0.2,
            "impact": 0.2,
            "urgency": 0.1,
            "estimated_cost": 0.7,
        })
        result = self.coordinator.deliberate(
            low_value,
            cycle_id="cycle-1",
            investigation_store=self.store,
            context=AutonomyContext(failed_cycles=2),
        )
        self.assertEqual("analyze_recent_failure", result["selected_goal_id"])
        self.assertFalse(result["curiosity_goal_selected"])
        self.assertEqual([], self.store.open_investigations())

    def test_homeostatic_cycle_must_match_and_explicit_pressure_overrides_derived(self):
        proposal = HomeostaticProposal(
            cycle_id="other-cycle",
            adjustments={},
            deviations={"prediction_error": 0.9},
            persistence={"prediction_error": 3},
            evidence_refs=(),
            rationale=(),
        )
        with self.assertRaisesRegex(ValueError, "cycle_id must match"):
            self.coordinator.deliberate(
                self.mappings(), cycle_id="cycle-1", investigation_store=self.store,
                homeostatic_proposal=proposal,
            )

        proposal.cycle_id = "cycle-1"
        result = self.coordinator.deliberate(
            self.mappings(), cycle_id="cycle-1", investigation_store=self.store,
            homeostatic_proposal=proposal, stability_pressure=0.2,
        )
        self.assertAlmostEqual(0.2, result["stability_pressure"])
        self.assertEqual("explicit", result["stability_pressure_source"])

    def test_inferred_belief_evidence_is_preserved_in_selection_provenance(self):
        self.model.update(
            {"memory_gap": "tentative"},
            cycle_id="belief-cycle",
            evidence_refs={"memory_gap": "self-model:evidence-7"},
            statuses={"memory_gap": "inferred"},
            confidences={"memory_gap": 0.3},
        )
        result = self.coordinator.deliberate(
            self.mappings(), cycle_id="cycle-1", investigation_store=self.store,
        )
        self.assertEqual("self-model:evidence-7", result["selected_provenance"]["belief_evidence_ref"])
        self.assertIn("self-model:evidence-7", result["investigation"]["selection_reason"])

    def test_invalid_homeostatic_adjustment_is_rejected(self):
        proposal = HomeostaticProposal(
            cycle_id="cycle-1",
            adjustments={"curiosity": float("nan")},
            deviations={},
            persistence={},
            evidence_refs=(),
            rationale=(),
        )
        with self.assertRaisesRegex(ValueError, "finite number"):
            self.coordinator.deliberate(
                self.mappings(), cycle_id="cycle-1", investigation_store=self.store,
                homeostatic_proposal=proposal,
            )


if __name__ == "__main__":
    unittest.main()
