from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import (
    Connection,
    MNN,
    MNNCognitionAdapter,
    Unit,
    VirtualBrain,
)


class MNNCognitionAdapterTests(unittest.TestCase):
    def make_network(self) -> MNN:
        network = MNN()
        network.add_unit(Unit("text", activation="identity"))
        network.add_unit(Unit("signal", bias=0.5, activation="tanh"))
        network.add_connection(Connection("text-to-signal", "text", "signal", 1.0))
        return network

    def test_mnn_trace_is_persisted_inside_cognitive_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brain.sqlite"
            network = self.make_network()
            adapter = MNNCognitionAdapter(
                network,
                input_features={"text": "text_length"},
            )
            brain = VirtualBrain(path, cognition=adapter)
            result = brain.run_cycle("Machina observes event 42.", "Record it.")

            cognitive = next(
                event.artifact
                for event in result.events
                if event.event_type == "cognition.completed"
            )
            trace = cognitive.data["understanding"]["mnn_signal"]
            self.assertGreater(trace["features"]["text"], 0.0)
            self.assertEqual(trace["timestep"], 1)
            self.assertEqual(trace["snapshot"]["schema_version"], 1)
            self.assertIn("signal", trace["activations"])
            self.assertIn("numeric diagnostic", trace["interpretation"])
            plasticity = next(
                event.artifact
                for event in result.events
                if event.event_type == "mnn.plasticity_applied"
            )
            self.assertEqual(plasticity.data["change"]["reward"], 1.0)
            self.assertGreater(
                plasticity.data["change"]["snapshot"]["connections"][0]["weight"],
                trace["snapshot"]["connections"][0]["weight"],
            )
            self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
            brain.store.verify_integrity()
            brain.close()

    def test_adapter_rejects_unknown_units_and_features(self):
        network = self.make_network()
        with self.assertRaises(ValueError):
            MNNCognitionAdapter(network, input_features={"missing": "text_length"})
        with self.assertRaises(ValueError):
            MNNCognitionAdapter(network, input_features={"text": "semantic_understanding"})
        with self.assertRaises(ValueError):
            MNNCognitionAdapter(
                network,
                input_features={"text": "text_length"},
                delayed_reward="yes",
            )

    def test_delayed_reward_uses_persisted_eligibility_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            network = self.make_network()
            adapter = MNNCognitionAdapter(
                network,
                input_features={"text": "text_length"},
                delayed_reward=True,
            )
            brain = VirtualBrain(Path(directory) / "brain.sqlite", cognition=adapter)
            result = brain.run_cycle("A delayed outcome observation.", "Record it.")

            cognitive = next(
                event.artifact
                for event in result.events
                if event.event_type == "cognition.completed"
            )
            trace = cognitive.data["understanding"]["mnn_signal"]
            self.assertEqual(trace["credit_assignment"], "delayed eligibility")
            self.assertEqual(trace["pending_steps"], 1)
            self.assertEqual(trace["experience_snapshot"]["pending_steps"], 1)

            plasticity = next(
                event.artifact
                for event in result.events
                if event.event_type == "mnn.plasticity_applied"
            )
            change = plasticity.data["change"]
            self.assertEqual(change["credit_assignment"], "delayed eligibility")
            self.assertEqual(change["pending_steps"], 1)
            self.assertEqual(change["experience_snapshot"]["pending_steps"], 0)
            self.assertGreater(change["weight_deltas"]["text-to-signal"], 0.0)
            self.assertGreater(
                change["snapshot"]["connections"][0]["weight"],
                trace["snapshot"]["connections"][0]["weight"],
            )
            self.assertEqual(adapter.cycle.pending_steps, 0)
            self.assertEqual(adapter.cycle.modulator.eligibility, {})
            self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
            brain.store.verify_integrity()
            brain.close()

    def test_adapter_enforces_max_pending_steps(self):
        adapter = MNNCognitionAdapter(
            self.make_network(),
            input_features={"text": "text_length"},
            delayed_reward=True,
            max_pending_steps=1,
        )
        adapter.cycle.step({"text": 0.5})
        with self.assertRaisesRegex(RuntimeError, "max pending steps"):
            adapter.cycle.step({"text": 0.5})
        with self.assertRaisesRegex(ValueError, "requires delayed_reward"):
            MNNCognitionAdapter(
                self.make_network(),
                input_features={"text": "text_length"},
                max_pending_steps=1,
            )

    def test_adapter_can_abort_an_orphaned_delayed_experience(self):
        network = self.make_network()
        adapter = MNNCognitionAdapter(
            network,
            input_features={"text": "text_length"},
            delayed_reward=True,
        )
        adapter.cycle.step({"text": 0.5})
        initial_weight = network.connections["text-to-signal"].weight

        result = adapter.abort_pending_experience()

        self.assertEqual(result["pending_steps"], 1)
        self.assertEqual(result["discarded_edges"], ["text-to-signal"])
        self.assertEqual(
            adapter.network.connections["text-to-signal"].weight, initial_weight
        )
        self.assertEqual(adapter.cycle.pending_steps, 0)
        self.assertEqual(adapter.cycle.modulator.eligibility, {})

        immediate = MNNCognitionAdapter(
            self.make_network(), input_features={"text": "text_length"}
        )
        with self.assertRaisesRegex(RuntimeError, "delayed reward is not enabled"):
            immediate.abort_pending_experience()

    def test_resume_before_delayed_reward_restores_pending_eligibility(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brain.sqlite"
            first_adapter = MNNCognitionAdapter(
                self.make_network(),
                input_features={"text": "text_length"},
                delayed_reward=True,
            )
            first_brain = VirtualBrain(path, cognition=first_adapter)
            cycle_id = first_brain.start_cycle(
                "Interrupted before the delayed reward.", "Test resume"
            )
            paused = first_brain.advance(cycle_id, stop_after="cognition.completed")
            self.assertIsNone(paused)
            initial_weight = first_adapter.network.connections["text-to-signal"].weight
            self.assertEqual(initial_weight, 1.0)
            self.assertEqual(first_adapter.cycle.pending_steps, 1)
            first_brain.close()

            restarted_adapter = MNNCognitionAdapter(
                self.make_network(),
                input_features={"text": "text_length"},
                delayed_reward=True,
            )
            restarted_brain = VirtualBrain(path, cognition=restarted_adapter)
            result = restarted_brain.resume(cycle_id)

            self.assertEqual(result.status, "completed")
            plasticity_events = [
                event for event in result.events
                if event.event_type == "mnn.plasticity_applied"
            ]
            self.assertEqual(len(plasticity_events), 1)
            change = plasticity_events[0].artifact.data["change"]
            self.assertEqual(change["pending_steps"], 1)
            self.assertEqual(change["experience_snapshot"]["pending_steps"], 0)
            self.assertGreater(change["weight_deltas"]["text-to-signal"], 0.0)
            self.assertGreater(
                restarted_adapter.network.connections["text-to-signal"].weight,
                initial_weight,
            )
            self.assertEqual(restarted_adapter.cycle.pending_steps, 0)
            self.assertTrue(restarted_brain.audit_cycle(cycle_id).valid)
            restarted_brain.store.verify_integrity()
            restarted_brain.close()

    def test_mnn_state_restores_from_journal_after_process_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brain.sqlite"
            first_network = self.make_network()
            first_adapter = MNNCognitionAdapter(
                first_network,
                input_features={"text": "text_length"},
            )
            first_brain = VirtualBrain(path, cognition=first_adapter)
            first_result = first_brain.run_cycle("First observation", "Record it")
            first_cognitive = next(
                event.artifact
                for event in first_result.events
                if event.event_type == "cognition.completed"
            )
            first_snapshot = first_cognitive.data["understanding"]["mnn_signal"]["snapshot"]
            self.assertEqual(first_snapshot["timestep"], 1)
            first_plasticity = next(
                event.artifact
                for event in first_result.events
                if event.event_type == "mnn.plasticity_applied"
            )
            persisted_snapshot = first_plasticity.data["change"]["snapshot"]
            first_brain.close()

            restarted_network = self.make_network()
            restarted_adapter = MNNCognitionAdapter(
                restarted_network,
                input_features={"text": "text_length"},
            )
            restarted_brain = VirtualBrain(path, cognition=restarted_adapter)
            second_result = restarted_brain.run_cycle("Second observation", "Record it")
            second_cognitive = next(
                event.artifact
                for event in second_result.events
                if event.event_type == "cognition.completed"
            )
            second_snapshot = second_cognitive.data["understanding"]["mnn_signal"]["snapshot"]
            self.assertEqual(second_snapshot["timestep"], 2)
            self.assertEqual(
                second_snapshot["connections"][0]["weight"],
                persisted_snapshot["connections"][0]["weight"],
            )
            self.assertTrue(restarted_brain.audit_cycle(second_result.cycle_id).valid)
            restarted_brain.store.verify_integrity()
            restarted_brain.close()

    def test_failed_outcome_applies_negative_reward_without_semantic_consolidation(self):
        class FailingExecutor:
            def execute(self, intent):
                raise RuntimeError("controlled test failure")

        with tempfile.TemporaryDirectory() as directory:
            network = self.make_network()
            adapter = MNNCognitionAdapter(
                network,
                input_features={"text": "text_length"},
            )
            brain = VirtualBrain(
                Path(directory) / "brain.sqlite",
                cognition=adapter,
                action_executor=FailingExecutor(),
            )
            result = brain.run_cycle("A failed observation action.", "Observe failure")
            plasticity = next(
                event.artifact
                for event in result.events
                if event.event_type == "mnn.plasticity_applied"
            )
            validation = next(
                event.artifact
                for event in result.events
                if event.event_type == "consolidation.validated"
            )
            self.assertEqual(validation.data["status"], "rejected")
            self.assertEqual(plasticity.data["change"]["reward"], -1.0)
            self.assertEqual(plasticity.data["change"]["validation_status"], "rejected")
            self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
            brain.store.verify_integrity()
            brain.close()

    def test_resume_after_plasticity_does_not_apply_reward_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            network = self.make_network()
            adapter = MNNCognitionAdapter(
                network,
                input_features={"text": "text_length"},
            )
            brain = VirtualBrain(Path(directory) / "brain.sqlite", cognition=adapter)
            cycle_id = brain.start_cycle("Persist the learning boundary.", "Test resume")
            paused = brain.advance(cycle_id, stop_after="mnn.plasticity_applied")
            self.assertIsNone(paused)
            weight_after_update = adapter.network.connections["text-to-signal"].weight
            events_after_pause = [
                event for event in brain.store.events_for_cycle(cycle_id)
                if event.event_type == "mnn.plasticity_applied"
            ]
            self.assertEqual(len(events_after_pause), 1)

            result = brain.resume(cycle_id)
            self.assertEqual(result.status, "completed")
            self.assertEqual(
                adapter.network.connections["text-to-signal"].weight,
                weight_after_update,
            )
            events_after_resume = [
                event for event in brain.store.events_for_cycle(cycle_id)
                if event.event_type == "mnn.plasticity_applied"
            ]
            self.assertEqual(len(events_after_resume), 1)
            self.assertTrue(brain.audit_cycle(cycle_id).valid)
            brain.store.verify_integrity()
            brain.close()


if __name__ == "__main__":
    unittest.main()
