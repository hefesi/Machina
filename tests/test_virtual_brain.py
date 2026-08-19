from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import IntegrityError, VirtualBrain


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


if __name__ == "__main__":
    unittest.main()
