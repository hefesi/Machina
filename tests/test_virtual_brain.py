from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import (
    AutonomyContext, AutonomyController, IntegrityError, InternalDeliberator,
    PersistentGoalStore, VirtualBrain, HomeostaticProposal, SelfHistoryInfluence, SelfStateTransition,
    MotivationSystem, MotivationalDrive,
)


class FailingExecutor:
    def execute(self, intent):
        raise RuntimeError("tool is unavailable")


class CountingExecutor:
    """External-effect stand-in which honors the ActionIntent idempotency key."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = {}

    def execute(self, intent):
        self.calls[intent.id] = self.calls.get(intent.id, 0) + 1
        return {
            "status": "succeeded",
            "actual_action": {"action": intent.data["action"]},
            "observed_result": {"call_count": self.calls[intent.id]},
            "errors": [],
            "side_effects": [],
            "executed_at": "2026-01-01T00:00:00+00:00",
            "evidence": [{"executor": "counting", "intent_id": intent.id}],
        }


class VirtualBrainLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temporary_directory.name) / "brain.sqlite"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_evaluated_explicit_fulfillment_updates_motivation_once_across_restart(self) -> None:
        def make_motivation():
            return MotivationSystem(drives=[
                MotivationalDrive(
                    "curiosity", level=0.8, setpoint=0.2,
                    recovery_rate=0.0, relief_gain=0.25,
                )
            ])

        original_motivation = make_motivation()
        brain = VirtualBrain(self.database_path, motivation_system=original_motivation)
        cycle_id = brain.start_cycle(
            "An observed outcome.",
            {
                "description": "Evaluate a curiosity task.",
                "motivational_fulfillment": {"curiosity": 0.8},
            },
        )
        self.assertIsNone(brain.advance(cycle_id, stop_after="motivation.feedback_applied"))
        self.assertEqual(1, brain.motivation_system.timestep)
        self.assertAlmostEqual(0.6, brain.motivation_system.drives["curiosity"].level)
        self.assertIs(original_motivation, brain.motivation_system)
        feedback_events = [
            event for event in brain.store.events_for_cycle(cycle_id)
            if event.event_type == "motivation.feedback_applied"
        ]
        self.assertEqual(1, len(feedback_events))
        brain.close()

        restarted = VirtualBrain(self.database_path, motivation_system=make_motivation())
        result = restarted.resume(cycle_id)
        self.assertEqual("completed", result.status)
        self.assertEqual(1, restarted.motivation_system.timestep)
        self.assertAlmostEqual(0.6, restarted.motivation_system.drives["curiosity"].level)
        feedback_events = [
            event for event in result.events
            if event.event_type == "motivation.feedback_applied"
        ]
        self.assertEqual(1, len(feedback_events))
        self.assertEqual(
            {"curiosity": 0.8},
            feedback_events[0].artifact.data["fulfillment"],
        )
        self.assertTrue(restarted.audit_cycle(cycle_id).valid)
        restarted.close()

    def test_motivation_does_not_infer_fulfillment_from_success(self) -> None:
        motivation = MotivationSystem(drives=[
            MotivationalDrive("curiosity", level=0.7, setpoint=0.2, recovery_rate=0.0)
        ])
        brain = VirtualBrain(self.database_path, motivation_system=motivation)
        result = brain.run_cycle("Observation", {"description": "Task completed."})
        feedback = next(
            event.artifact for event in result.events
            if event.event_type == "motivation.feedback_applied"
        )
        self.assertTrue(feedback.data["success"])
        self.assertEqual({}, feedback.data["fulfillment"])
        self.assertAlmostEqual(0.7, brain.motivation_system.drives["curiosity"].level)
        brain.close()

    def test_complete_loop_is_durable_and_causally_connected(self) -> None:
        brain = VirtualBrain(self.database_path)
        result = brain.run_cycle(
            "Water boils at 100 C at standard pressure.",
            "Record the observation safely.",
        )

        self.assertEqual(result.status, "completed")
        self.assertIsNotNone(result.experience_id)
        self.assertIsNotNone(result.model_update_id)

        event_types = [event.event_type for event in result.events]
        expected = [
            "observation.received",
            "goal.activated",
            "cycle.started",
            "workspace.updated",
            "memory.retrieval_requested",
            "memory.retrieved",
            "cognition.requested",
            "cognition.completed",
            "workspace.cognition_updated",
            "decision.requested",
            "decision.made",
            "action.intent_created",
            "action.execution_started",
            "action.result",
            "experience.created",
            "memory.episode_recorded",
            "evaluation.completed",
            "learning.proposed",
            "consolidation.validated",
            "memory.consolidated",
            "model.updated",
            "cycle.completed",
        ]
        self.assertEqual(event_types, expected)

        artifacts = {event.artifact.id: event.artifact for event in result.events}
        for artifact in artifacts.values():
            for reference in artifact.input_refs:
                self.assertIn(reference, artifacts, f"missing causal input {reference}")

        brain.store.verify_integrity()
        audit = brain.audit_cycle(result.cycle_id)
        self.assertTrue(audit.valid, audit.errors)
        brain.close()

    def test_memory_is_retrieved_in_a_later_cycle_after_restart(self) -> None:
        brain = VirtualBrain(self.database_path)
        first = brain.run_cycle("Mars is a planet.", "Remember the fact.")
        brain.close()

        restarted = VirtualBrain(self.database_path)
        second = restarted.run_cycle("What is Mars?", "Use relevant memory.")
        retrieval = next(
            event.artifact
            for event in second.events
            if event.event_type == "memory.retrieved"
        )
        self.assertGreaterEqual(len(retrieval.data["memory_ids"]), 1)
        self.assertEqual(first.status, "completed")
        restarted.store.verify_integrity()
        self.assertTrue(restarted.audit_cycle(second.cycle_id).valid)
        restarted.close()

    def test_failed_action_still_becomes_result_experience_and_rejected_learning(self) -> None:
        brain = VirtualBrain(self.database_path, action_executor=FailingExecutor())
        result = brain.run_cycle("Attempt a controlled action.", "Observe failure.")

        action_result = next(
            event.artifact for event in result.events if event.event_type == "action.result"
        )
        experience = next(
            event.artifact for event in result.events if event.event_type == "experience.created"
        )
        validation = next(
            event.artifact
            for event in result.events
            if event.event_type == "consolidation.validated"
        )
        self.assertEqual(action_result.data["status"], "failed")
        self.assertEqual(experience.data["action_result_ref"], action_result.id)
        self.assertEqual(validation.data["status"], "rejected")
        self.assertIsNone(result.model_update_id)
        self.assertIn("memory.episode_recorded", [event.event_type for event in result.events])
        brain.store.verify_integrity()
        self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
        brain.close()

    def test_pause_restart_and_resume_do_not_repeat_a_recorded_action(self) -> None:
        executor = CountingExecutor()
        brain = VirtualBrain(self.database_path, action_executor=executor)
        cycle_id = brain.start_cycle("Persist before restart.", "Test resumption.")
        paused = brain.advance(cycle_id, stop_after="action.result")
        self.assertIsNone(paused)
        intent = brain.store.latest_artifact(cycle_id, "action.intent_created")
        self.assertIsNotNone(intent)
        self.assertEqual(executor.calls[intent.id], 1)
        brain.close()

        restarted = VirtualBrain(self.database_path, action_executor=executor)
        result = restarted.resume(cycle_id)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "completed")
        self.assertEqual(executor.calls[intent.id], 1)
        self.assertIn("cycle.resumed", [event.event_type for event in result.events])
        restarted.store.verify_integrity()
        self.assertTrue(restarted.audit_cycle(cycle_id).valid)
        restarted.close()

    def test_memory_revisions_preserve_the_prior_version_and_provenance(self) -> None:
        brain = VirtualBrain(self.database_path)
        first = brain.run_cycle("A durable fact.", "Remember the same lesson.")
        second = brain.run_cycle("A durable fact again.", "Remember the same lesson.")

        records = [
            event.artifact
            for event in brain.store.all_events()
            if event.event_type == "memory.consolidated"
        ]
        self.assertEqual(len(records), 2)
        first_record, second_record = records
        self.assertEqual(first_record.data["record_version"], 1)
        self.assertEqual(second_record.data["record_version"], 2)
        self.assertEqual(second_record.data["supersedes"], first_record.id)
        self.assertTrue(first_record.source_refs)
        self.assertTrue(brain.audit_cycle(first.cycle_id).valid)
        self.assertTrue(brain.audit_cycle(second.cycle_id).valid)
        brain.close()

    def test_append_only_trigger_and_hash_verifier_detect_tampering(self) -> None:
        brain = VirtualBrain(self.database_path)
        brain.run_cycle("Keep an audit trail.", "Test journal integrity.")
        with self.assertRaises(Exception):
            brain.store._connection.execute("UPDATE events SET event_type = 'tampered'")

        # The trigger blocks normal mutation; verify the independently
        # recomputed chain as well.
        brain.store.verify_integrity()
        brain.close()


    def test_deliberated_cycle_journals_selection_and_completes(self) -> None:
        goal_store = PersistentGoalStore(
            Path(self.temporary_directory.name) / "internal-goals.sqlite"
        )
        deliberator = InternalDeliberator(AutonomyController(), goal_store)
        brain = VirtualBrain(
            self.database_path,
            internal_deliberator=deliberator,
        )
        result = brain.run_deliberated_cycle(
            "Internal state: several unresolved questions.",
            AutonomyContext(unresolved_questions=2, cycles_since_reflection=4),
        )
        self.assertEqual("completed", result.status)
        trace = next(
            event.artifact for event in result.events
            if event.event_type == "goal.deliberated"
        )
        self.assertIn("deliberation", trace.data)
        self.assertIn("internal_goal_id", trace.data)
        self.assertEqual("internal_deliberator", trace.producer)
        self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
        self.assertEqual(1, goal_store.summary()["active"])
        brain.close()
        goal_store.close()


    def test_homeostatic_proposal_is_journaled_with_deliberation(self) -> None:
        goal_store = PersistentGoalStore(
            Path(self.temporary_directory.name) / "homeostatic-goals.sqlite"
        )
        deliberator = InternalDeliberator(AutonomyController(), goal_store)
        brain = VirtualBrain(self.database_path, internal_deliberator=deliberator)
        proposal = HomeostaticProposal(
            cycle_id="self-cycle-12",
            adjustments={"error_recovery": 0.12},
            deviations={"prediction_error": 0.4},
            persistence={"prediction_error": 3},
            evidence_refs=("step:12",),
            rationale=("prediction error remained above range",),
        )
        result = brain.run_deliberated_cycle(
            "Elevated internal prediction error.",
            AutonomyContext(failed_cycles=1),
            homeostatic_proposal=proposal,
        )
        trace = next(event.artifact for event in result.events if event.event_type == "goal.deliberated")
        self.assertEqual("self-cycle-12", trace.data["homeostatic_regulation"]["cycle_id"])
        self.assertEqual(["step:12"], trace.data["homeostatic_regulation"]["evidence_refs"])
        failure_option = next(item for item in trace.data["deliberation"]["autonomy"]["alternatives"] if item["goal"]["drive"] == "error_recovery")
        self.assertAlmostEqual(0.12, failure_option["score"]["feedback_adjustment"])
        self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
        brain.close()
        goal_store.close()


    def test_self_history_influence_is_applied_and_journaled(self) -> None:
        goal_store = PersistentGoalStore(
            Path(self.temporary_directory.name) / "self-history-goals.sqlite"
        )
        deliberator = InternalDeliberator(AutonomyController(), goal_store)
        brain = VirtualBrain(self.database_path, internal_deliberator=deliberator)
        transition = SelfStateTransition(
            "internal.mnn.prediction_error", 0.2, 0.8,
            "self-cycle-1", "self-cycle-3", 3,
            "persistent_since_change", ("telemetry:1", "telemetry:3"),
        )
        influence = SelfHistoryInfluence(
            adjustments={"error_recovery": 0.08},
            transitions=(transition,),
            evidence_refs=("telemetry:1", "telemetry:3"),
            rationale=("persistent prediction error in Self history",),
        )
        result = brain.run_deliberated_cycle(
            "Review persistent internal prediction error.",
            AutonomyContext(failed_cycles=1),
            self_history_influence=influence,
        )
        trace = next(event.artifact for event in result.events if event.event_type == "goal.deliberated")
        self.assertEqual({"error_recovery": 0.08}, trace.data["self_history_influence"]["adjustments"])
        self.assertEqual(["telemetry:1", "telemetry:3"], trace.data["self_history_influence"]["evidence_refs"])
        option = next(item for item in trace.data["deliberation"]["autonomy"]["alternatives"] if item["goal"]["drive"] == "error_recovery")
        self.assertAlmostEqual(0.08, option["score"]["feedback_adjustment"])
        self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
        brain.close()
        goal_store.close()

    def test_deliberated_cycle_requires_explicit_configuration(self) -> None:
        brain = VirtualBrain(self.database_path)
        with self.assertRaises(RuntimeError):
            brain.run_deliberated_cycle("state", AutonomyContext())
        brain.close()


    def test_curiosity_investigation_is_linked_to_brain_journal_and_survives_restart(self) -> None:
        curiosity_path = Path(self.temporary_directory.name) / "curiosity.sqlite"
        brain = VirtualBrain(
            self.database_path,
            curiosity_investigation_path=curiosity_path,
        )
        cycle = brain.run_cycle("An unresolved memory question.", "Record the context.")
        started = brain.start_curiosity_investigation(
            cycle.cycle_id, "brain-investigation-1",
            gap_property="memory_recall",
            question="Which fragments improve recall?",
            hypothesis="Temporal indexing may improve retrieval.",
            selection_reason="High information gain with low external risk.",
            goal_id="curiosity:memory-recall",
        )
        self.assertEqual("open", started["status"])
        evidence = brain.record_curiosity_evidence(
            cycle.cycle_id, "brain-investigation-1",
            evidence_ref="experiment:recall-01",
            finding="Indexed fragments ranked higher in this test.",
        )
        self.assertEqual("experiment:recall-01", evidence["evidence_ref"])
        closed = brain.close_curiosity_investigation(
            cycle.cycle_id, "brain-investigation-1",
            outcome="partially_answered",
            answer_summary="Initial evidence supports further testing.",
            remaining_unknowns=["Performance on longer histories"],
        )
        self.assertEqual("partially_answered", closed["outcome"])
        self.assertTrue(brain.audit_cycle(cycle.cycle_id).valid)
        event_types = [event.event_type for event in brain.store.events_for_cycle(cycle.cycle_id)]
        self.assertEqual(1, event_types.count("curiosity.investigation_started"))
        self.assertEqual(1, event_types.count("curiosity.evidence_recorded"))
        self.assertEqual(1, event_types.count("curiosity.investigation_closed"))
        brain.close()

        restarted = VirtualBrain(
            self.database_path,
            curiosity_investigation_path=curiosity_path,
        )
        history = restarted.curiosity_store.history()
        self.assertEqual("brain-investigation-1", history[0]["investigation_id"])
        self.assertEqual("experiment:recall-01", history[0]["evidence"][0]["evidence_ref"])
        journal_events = restarted.store.events_for_cycle(cycle.cycle_id)
        self.assertEqual(
            ["curiosity.investigation_started", "curiosity.evidence_recorded", "curiosity.investigation_closed"],
            [event.event_type for event in journal_events if event.event_type.startswith("curiosity.")],
        )
        restarted.close()

    def test_curiosity_journaling_requires_explicit_store_configuration(self) -> None:
        brain = VirtualBrain(self.database_path)
        cycle = brain.run_cycle("Context", "Complete a simple cycle.")
        with self.assertRaisesRegex(RuntimeError, "curiosity investigation memory is disabled"):
            brain.start_curiosity_investigation(
                cycle.cycle_id, "missing-store",
                gap_property="test", question="Why?",
                hypothesis="Unknown", selection_reason="Explore uncertainty",
                goal_id="curiosity:test",
            )
        brain.close()



if __name__ == "__main__":
    unittest.main()
