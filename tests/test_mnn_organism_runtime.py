from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import (
    MNN,
    MNNOrganism,
    MotivationalDrive,
    MotivationSystem,
    Unit,
    build_mnn_organism_runtime,
    AutonomyContext,
    AutonomyController,
    InternalDeliberator,
    PersistentGoalStore,
    VirtualBrain,
    NormalizedPerception,
    CausalExperimentStore,
)


class MNNOrganismRuntimeTests(unittest.TestCase):
    def make_organism(self) -> MNNOrganism:
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        network.add_unit(Unit("memory", activation="tanh"))
        motivation = MotivationSystem(drives=[
            MotivationalDrive("curiosity", level=0.9, setpoint=0.2),
            MotivationalDrive("stability", level=0.3, setpoint=0.2),
        ])
        return MNNOrganism(
            "runtime-test",
            network=network,
            motivation=motivation,
            learning_rate=0.0,
        )

    def test_factory_wires_both_adapters_to_same_organism(self):
        organism = self.make_organism()
        runtime = build_mnn_organism_runtime(
            organism,
            input_features={"sensor": "text_length"},
            target_unit="memory",
        )
        self.assertIs(runtime.organism, organism)
        self.assertIs(runtime.cognition.organism, organism)
        self.assertIs(runtime.agency.organism, organism)
        self.assertIs(runtime.motivation, organism.motivation)

    def test_motivation_is_exposed_as_bounded_goal_adjustments(self):
        runtime = build_mnn_organism_runtime(
            self.make_organism(),
            input_features={"sensor": "text_length"},
            target_unit="memory",
        )
        adjustments = runtime.drive_adjustments()
        self.assertIn("curiosity", adjustments)
        self.assertIn("stability", adjustments)
        self.assertTrue(all(-0.3 <= value <= 0.3 for value in adjustments.values()))
        self.assertEqual(runtime.ranked_drives()[0][0], "curiosity")

    def test_runtime_without_motivation_returns_empty_signals(self):
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        organism = MNNOrganism("runtime-no-motivation", network=network)
        runtime = build_mnn_organism_runtime(
            organism,
            input_features={"sensor": "text_length"},
            target_unit="sensor",
        )
        self.assertIsNone(runtime.motivation)
        self.assertEqual(runtime.drive_adjustments(), {})
        self.assertEqual(runtime.ranked_drives(), [])

    def test_runtime_completes_integrated_cycle_with_one_motivational_tick(self):
        with tempfile.TemporaryDirectory() as directory:
            organism = self.make_organism()
            runtime = build_mnn_organism_runtime(
                organism,
                input_features={"sensor": "text_length"},
                target_unit="memory",
            )
            shared_motivation = organism.motivation
            goals = PersistentGoalStore(Path(directory) / "goals.sqlite")
            brain = VirtualBrain(
                Path(directory) / "brain.sqlite",
                cognition=runtime.cognition,
                agency=runtime.agency,
                internal_deliberator=InternalDeliberator(AutonomyController(), goals),
            )
            result = runtime.run_deliberated_cycle(
                brain,
                "Inspect this integrated cognitive cycle.",
                AutonomyContext(unresolved_questions=1),
                motivational_fulfillment={"curiosity": 0.5},
            )
            self.assertEqual("completed", result.status)
            self.assertIs(organism.motivation, shared_motivation)
            self.assertIs(brain.motivation_system, shared_motivation)
            self.assertIs(runtime.motivation, shared_motivation)
            self.assertEqual(1, shared_motivation.timestep)
            feedback = next(
                event.artifact for event in result.events
                if event.event_type == "motivation.feedback_applied"
            )
            self.assertEqual({"curiosity": 0.5}, feedback.data["fulfillment"])
            plasticity = next(
                event.artifact for event in result.events
                if event.event_type == "mnn.plasticity_applied"
            )
            self.assertEqual(
                [next(e.artifact.id for e in result.events if e.event_type == "evaluation.completed"),
                 next(e.artifact.id for e in result.events if e.event_type == "consolidation.validated")],
                list(plasticity.input_refs),
            )
            self.assertIn("prediction_error", plasticity.data["change"])
            self.assertIn("actual_outcome", plasticity.data["change"])
            self.assertEqual("approved", plasticity.data["change"]["validation_status"])
            self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
            brain.close()
            goals.close()

    def test_factory_rejects_non_organism(self):
        with self.assertRaises(TypeError):
            build_mnn_organism_runtime(
                object(),
                input_features={"sensor": "text_length"},
                target_unit="sensor",
            )

    def test_full_organism_cycle_from_normalized_perception_through_curiosity_and_causal_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            organism = self.make_organism()
            runtime = build_mnn_organism_runtime(
                organism,
                input_features={"sensor": "text_length"},
                target_unit="memory",
            )
            goals = PersistentGoalStore(Path(directory) / "goals.sqlite")
            causal = CausalExperimentStore(Path(directory) / "causal.sqlite")
            causal.register_experiment(
                "strategy-observation",
                design="observational",
                treatment_name="memory-guided",
                control_name="baseline",
                protocol_ref="protocol:observational-v1",
            )
            brain = VirtualBrain(
                Path(directory) / "brain.sqlite",
                cognition=runtime.cognition,
                agency=runtime.agency,
                internal_deliberator=InternalDeliberator(AutonomyController(), goals),
                curiosity_investigation_path=Path(directory) / "curiosity.sqlite",
                causal_experiment_store=causal,
            )
            try:
                brain.curiosity_store.start_investigation(
                    "open-question-1",
                    gap_property="navigation_uncertainty",
                    question="Which route is safer?",
                    hypothesis="The route with fewer obstacles is safer.",
                    selection_reason="Unresolved perception uncertainty.",
                    cycle_id="seed-cycle",
                    goal_id="seed-goal",
                )
                perception = NormalizedPerception(
                    content={"intent": "route_assessment", "text": "Compare the safer route and inspect obstacles."},
                    raw_payload={"transcript": "Compare the safer route and inspect obstacles."},
                    modality="audio_transcript",
                    source={"type": "microphone", "name": "test-mic", "reliability": 0.94},
                    confidence=0.87,
                    raw_reference="capture:integrated-e2e",
                    transformations=("speech_to_text", "intent_extraction"),
                )
                result = runtime.run_deliberated_cycle(
                    brain,
                    perception,
                    AutonomyContext(unresolved_questions=0),
                    strategy_experiment_id="strategy-observation",
                    motivational_fulfillment={"curiosity": 0.4},
                )
                self.assertEqual("completed", result.status)
                events = {event.event_type: event.artifact for event in result.events}
                observed = events["observation.received"]
                self.assertEqual("audio_transcript", observed.data["modality"])
                self.assertEqual("capture:integrated-e2e", observed.data["raw_reference"])
                self.assertEqual(0.87, observed.confidence)
                state = events["workspace.cognition_updated"].data["internal_state"]
                self.assertEqual(result.cycle_id, state["cycle_id"])
                self.assertIn("cognitive_result_ref", state)
                self.assertEqual(1, state["mnn_signal"]["timestep"])
                self.assertEqual(["open-question-1"], events["goal.deliberated"].data["curiosity_context"]["open_investigation_refs"])
                guidance = events["goal.deliberated"].data["strategy_guidance"]
                self.assertEqual("hold", guidance["guidance"])
                self.assertEqual("observational_association", guidance["classification"])
                self.assertFalse(guidance["policy_mutated"])
                self.assertEqual(1, organism.motivation.timestep)
                self.assertIn("decision.made", events)
                self.assertIn("action.result", events)
                self.assertIn("evaluation.completed", events)
                self.assertIn("mnn.plasticity_applied", events)
                self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
            finally:
                brain.close()
                goals.close()
                causal.close()


if __name__ == "__main__":
    unittest.main()
