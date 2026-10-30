from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from machina.chemical_signaling import ChemicalEvent, ChemicalSignaling, ChemicalState
from machina.mnn import Connection, MNN, Unit
from machina.mnn_motivation import MotivationSystem, MotivationalDrive
from machina.mnn_organism import DecisionOption, MNNOrganism
from machina.fragment_memory import FragmentMemory
from machina.self_continuity import SelfContinuity


class MNNOrganismTests(unittest.TestCase):
    def make_organism(self):
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        network.add_unit(Unit("dopamine", activation="identity"))
        network.add_unit(Unit("integrator", activation="tanh"))
        network.add_unit(Unit("memory_context", activation="identity"))
        network.add_connection(Connection("sensor-integrator", "sensor", "integrator", 0.4))
        network.add_connection(Connection("dopamine-integrator", "dopamine", "integrator", 0.2))
        network.add_connection(Connection("memory-integrator", "memory_context", "integrator", 0.3))
        return MNNOrganism(
            "machina-test",
            network,
            chemical_inputs={"dopamine": "dopamine"},
            learning_rate=0.01,
        )

    def test_one_tick_advances_all_subsystems_together(self):
        organism = self.make_organism()
        result = organism.step(
            {"sensor": 0.7},
            ChemicalEvent(reward=0.8, novelty=0.6, progress=0.4),
        )
        self.assertEqual(result.timestep, 1)
        self.assertEqual(organism.network.timestep, 1)
        self.assertEqual(organism.signaling.state.timestep, 1)
        self.assertEqual(len(organism.continuity.event_history), 1)
        self.assertIn("dopamine", result.neural_state)


    def test_motivation_is_coupled_to_chemistry_and_advances_with_organism(self):
        motivation = MotivationSystem([
            MotivationalDrive("curiosity", level=0.9, setpoint=0.9),
            MotivationalDrive("stability", level=0.7, setpoint=0.7),
        ])
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        organism = MNNOrganism(
            "motivated-test",
            network=network,
            motivation=motivation,
            chemical_inputs={"acetylcholine": "sensor"},
        )
        result = organism.step(fulfillment={"curiosity": 1.0})
        self.assertEqual(1, result.timestep)
        self.assertEqual(1, motivation.timestep)
        self.assertLess(result.motivation_urgencies["curiosity"], 0.9)
        self.assertGreater(result.chemical_state["acetylcholine"], 0.0)
        self.assertAlmostEqual(
            result.chemical_state["acetylcholine"],
            result.neural_state["sensor"],
        )

    def test_motivation_snapshot_round_trip_preserves_future_integrated_cycles(self):
        organism = MNNOrganism(
            "motivated-snapshot",
            motivation=MotivationSystem([
                MotivationalDrive("curiosity", level=0.8, setpoint=0.8)
            ]),
        )
        organism.step(event=ChemicalEvent(novelty=0.4), fulfillment={"curiosity": 0.2})
        snapshot = json.loads(json.dumps(organism.snapshot()))
        restored = MNNOrganism.from_snapshot(snapshot)
        self.assertEqual(snapshot, restored.snapshot())
        next_a = organism.step(event=ChemicalEvent(reward=0.7), fulfillment={"curiosity": 0.6})
        next_b = restored.step(event=ChemicalEvent(reward=0.7), fulfillment={"curiosity": 0.6})
        self.assertEqual(next_a, next_b)
        self.assertEqual(organism.snapshot(), restored.snapshot())

    def test_invalid_motivation_feedback_does_not_advance_any_organism_state(self):
        organism = MNNOrganism(
            "motivated-validation",
            motivation=MotivationSystem([MotivationalDrive("curiosity")]),
        )
        before = organism.snapshot()
        with self.assertRaises(ValueError):
            organism.step(fulfillment={"unknown-drive": 1.0})
        self.assertEqual(before, organism.snapshot())

    def test_motivation_clock_must_match_existing_organism_clock(self):
        network = MNN()
        network.timestep = 1
        with self.assertRaises(ValueError):
            MNNOrganism(
                "clock-mismatch",
                network=network,
                signaling=ChemicalSignaling(state=ChemicalState(timestep=1)),
                motivation=MotivationSystem([MotivationalDrive("curiosity")]),
            )

    def test_chemical_modulation_reaches_configured_neural_unit(self):
        organism = self.make_organism()
        result = organism.step(event=ChemicalEvent(reward=1.0))
        self.assertAlmostEqual(
            organism.network.units["dopamine"].state,
            result.chemical_state["dopamine"],
        )

    def test_snapshot_round_trip_preserves_coupled_state(self):
        organism = self.make_organism()
        organism.step({"sensor": 0.5}, ChemicalEvent(reward=0.9, novelty=0.3))
        snapshot = json.loads(json.dumps(organism.snapshot()))
        restored = MNNOrganism.from_snapshot(snapshot)
        self.assertEqual(restored.snapshot(), snapshot)
        next_a = organism.step({"sensor": 0.2}, ChemicalEvent(reward=0.1))
        next_b = restored.step({"sensor": 0.2}, ChemicalEvent(reward=0.1))
        self.assertEqual(next_a, next_b)
        self.assertEqual(organism.snapshot(), restored.snapshot())

    def test_invalid_input_does_not_advance_any_subsystem(self):
        organism = self.make_organism()
        before = organism.snapshot()
        with self.assertRaises(ValueError):
            organism.step({"missing": 1.0})
        self.assertEqual(organism.snapshot(), before)

    def test_rejects_mismatched_identity_or_clocks(self):
        with self.assertRaises(ValueError):
            MNNOrganism("a", continuity=SelfContinuity("b"))
        network = MNN()
        network.timestep = 1
        with self.assertRaises(ValueError):
            MNNOrganism("a", network=network)

    def test_chemical_routes_must_reference_real_units(self):
        with self.assertRaises(ValueError):
            MNNOrganism("a", chemical_inputs={"dopamine": "missing"})


    def test_transitions_are_archived_as_episodic_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "episodes.sqlite3"
            memory = FragmentMemory(path)
            organism = self.make_organism()
            organism.memory = memory
            first = organism.step({"sensor": 0.5}, ChemicalEvent(reward=0.8))
            second = organism.step({"sensor": 0.2}, ChemicalEvent(reward=0.1))
            self.assertEqual(2, memory.count())
            recalled = organism.recall_experiences("prediction error", limit=5)
            self.assertEqual(2, len(recalled))
            self.assertEqual(
                {first.timestep, second.timestep},
                {item.metadata["timestep"] for item in recalled},
            )
            memory.close()
            reopened = FragmentMemory(path)
            self.assertEqual(2, reopened.count())
            self.assertEqual(2, len(reopened.recall("MNN organism experience")))
            reopened.close()


    def test_memory_guidance_is_explicit_and_reaches_neural_input(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = FragmentMemory(Path(directory) / "episodes.sqlite3")
            organism = self.make_organism()
            organism.memory = memory
            organism.step({"sensor": 0.6}, ChemicalEvent(reward=0.8))
            before = organism.snapshot()
            guidance = organism.prepare_memory_guidance(
                "prediction error", target_unit="memory_context"
            )
            self.assertTrue(guidance.evidence_ids)
            self.assertGreater(guidance.signal, 0.0)
            self.assertLessEqual(guidance.signal, 1.0)
            self.assertEqual(before, organism.snapshot())
            result = organism.step(memory_guidance=guidance)
            self.assertAlmostEqual(result.neural_state["memory_context"], guidance.signal)
            self.assertEqual(2, memory.count())
            memory.close()

    def test_unrelated_memory_query_abstains_with_zero_signal(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = FragmentMemory(Path(directory) / "episodes.sqlite3")
            organism = self.make_organism()
            organism.memory = memory
            organism.step({"sensor": 0.6})
            guidance = organism.prepare_memory_guidance(
                "volcano astronomy", target_unit="memory_context"
            )
            self.assertEqual((), guidance.evidence_ids)
            self.assertEqual(0.0, guidance.signal)
            memory.close()

    def test_memory_guidance_rejects_conflicting_or_invalid_routes(self):
        organism = self.make_organism()
        with tempfile.TemporaryDirectory() as directory:
            organism.memory = FragmentMemory(Path(directory) / "episodes.sqlite3")
            organism.step({"sensor": 0.4})
            guidance = organism.prepare_memory_guidance(
                "prediction error", target_unit="memory_context"
            )
            with self.assertRaises(ValueError):
                organism.step({"memory_context": 0.2}, memory_guidance=guidance)
            with self.assertRaises(ValueError):
                organism.prepare_memory_guidance("query", target_unit="missing")
            organism.memory.close()


    def test_memory_guidance_feedback_learns_contextual_usefulness_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = FragmentMemory(Path(directory) / "episodes.sqlite3")
            organism = self.make_organism()
            organism.memory = memory
            organism.step({"sensor": 0.6})
            guidance = organism.prepare_memory_guidance(
                "prediction error", target_unit="memory_context"
            )
            fragment_id = guidance.evidence_ids[0]
            contextual_before = organism.prepare_memory_guidance(
                "prediction error rareword", target_unit="memory_context", context="task-a"
            )
            before = memory.context_importance(fragment_id, "task-a")
            result, applied = organism.evaluate_memory_guidance(
                guidance, {fragment_id: True},
                context="task-a", operation_id="evaluation-001",
                strength=0.15,
            )
            self.assertTrue(applied)
            self.assertAlmostEqual(before + 0.15, result[fragment_id])
            self.assertAlmostEqual(before + 0.15, memory.context_importance(fragment_id, "task-a"))
            contextual_after = organism.prepare_memory_guidance(
                "prediction error", target_unit="memory_context", context="task-a"
            )
            self.assertGreater(contextual_after.signal, contextual_before.signal)
            repeated, applied_again = organism.evaluate_memory_guidance(
                guidance, {fragment_id: True},
                context="task-a", operation_id="evaluation-001",
                strength=0.15,
            )
            self.assertFalse(applied_again)
            self.assertEqual(result, repeated)
            self.assertAlmostEqual(before + 0.15, memory.context_importance(fragment_id, "task-a"))
            self.assertAlmostEqual(0.5, memory.context_importance(fragment_id, "task-b"))
            memory.close()

    def test_memory_feedback_rejects_unrelated_evidence_and_non_boolean_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = FragmentMemory(Path(directory) / "episodes.sqlite3")
            organism = self.make_organism()
            organism.memory = memory
            organism.step({"sensor": 0.6})
            guidance = organism.prepare_memory_guidance(
                "prediction error", target_unit="memory_context"
            )
            with self.assertRaises(ValueError):
                organism.evaluate_memory_guidance(
                    guidance, {"not-in-evidence": True},
                    context="task-a", operation_id="bad-001",
                )
            with self.assertRaises(ValueError):
                organism.evaluate_memory_guidance(
                    guidance, {guidance.evidence_ids[0]: 1},
                    context="task-a", operation_id="bad-002",
                )
            memory.close()


    def test_memory_guided_decision_can_change_ranking_and_returns_auditable_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            memory = FragmentMemory(Path(directory) / "episodes.sqlite3")
            organism = self.make_organism()
            organism.memory = memory
            organism.step({"sensor": 0.6})
            options = [
                DecisionOption("reuse-experience", 0.40, "prediction error"),
                DecisionOption("unfamiliar-route", 0.55, "volcano astronomy"),
            ]
            assessment = organism.assess_decisions(
                options,
                target_unit="memory_context",
                context="route-planning",
                memory_weight=0.25,
            )
            self.assertEqual("reuse-experience", assessment.selected_action)
            self.assertGreater(
                assessment.scores["reuse-experience"],
                assessment.base_utilities["reuse-experience"],
            )
            self.assertEqual((), assessment.evidence_ids["unfamiliar-route"])
            self.assertEqual(
                assessment.evidence_ids["reuse-experience"],
                assessment.selected_guidance.evidence_ids,
            )
            # The assessment is deliberative only: it does not advance the organism.
            self.assertEqual(1, organism.timestep)
            memory.close()

    def test_decision_assessment_without_memory_does_not_execute_actions(self):
        organism = self.make_organism()
        with tempfile.TemporaryDirectory() as directory:
            organism.memory = FragmentMemory(Path(directory) / "episodes.sqlite3")
            result = organism.assess_decisions(
                [
                    DecisionOption("a", 0.2, "nothing"),
                    DecisionOption("b", 0.8, "unrelated"),
                ],
                target_unit="memory_context",
                context="test",
            )
            self.assertEqual("b", result.selected_action)
            self.assertEqual(0, organism.timestep)
            organism.memory.close()

    def test_memory_is_optional_and_recall_requires_attachment(self):
        organism = self.make_organism()
        organism.step({"sensor": 0.1})
        with self.assertRaises(RuntimeError):
            organism.recall_experiences("anything")

if __name__ == "__main__":
    unittest.main()
