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


if __name__ == "__main__":
    unittest.main()
