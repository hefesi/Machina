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
