from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import (
    Connection,
    MNN,
    MNNOrganism,
    MNNOrganismCognitionAdapter,
    Unit,
    VirtualBrain,
)


class MNNOrganismCognitionAdapterTests(unittest.TestCase):
    def make_organism(self) -> MNNOrganism:
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        network.add_unit(Unit("integrator", activation="tanh"))
        network.add_connection(
            Connection("sensor-integrator", "sensor", "integrator", 0.4)
        )
        return MNNOrganism(
            "machina-bridge-test",
            network=network,
            learning_rate=0.0,
        )

    def test_organism_transition_is_journaled_inside_cognitive_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            organism = self.make_organism()
            adapter = MNNOrganismCognitionAdapter(
                organism,
                input_features={"sensor": "text_length"},
            )
            brain = VirtualBrain(
                Path(directory) / "brain.sqlite",
                cognition=adapter,
            )
            result = brain.run_cycle(
                "Machina observes a new event.",
                "Process the observation.",
            )

            cognitive = next(
                event.artifact
                for event in result.events
                if event.event_type == "cognition.completed"
            )
            trace = cognitive.data["understanding"]["mnn_signal"]
            self.assertEqual(trace["timestep"], 1)
            self.assertIn("integrator", trace["activations"])
            self.assertEqual(
                trace["snapshot"]["agent_id"],
                "machina-bridge-test",
            )
            self.assertIn("prediction_error", trace["organism_state"])

            plasticity = next(
                event.artifact
                for event in result.events
                if event.event_type == "mnn.plasticity_applied"
            )
            self.assertEqual(plasticity.data["change"]["reward"], 1.0)
            self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
            brain.store.verify_integrity()
            brain.close()

    def test_organism_state_restores_from_journal_after_process_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "brain.sqlite"

            first_adapter = MNNOrganismCognitionAdapter(
                self.make_organism(),
                input_features={"sensor": "text_length"},
            )
            first_brain = VirtualBrain(path, cognition=first_adapter)
            first = first_brain.run_cycle("First observation.", "Record it.")
            first_update = next(
                event.artifact
                for event in first.events
                if event.event_type == "mnn.plasticity_applied"
            )
            saved = first_update.data["change"]["snapshot"]
            self.assertEqual(saved["network"]["timestep"], 1)
            first_brain.close()

            restarted_adapter = MNNOrganismCognitionAdapter(
                self.make_organism(),
                input_features={"sensor": "text_length"},
            )
            restarted_brain = VirtualBrain(path, cognition=restarted_adapter)
            second = restarted_brain.run_cycle("Second observation.", "Record it.")
            second_cognitive = next(
                event.artifact
                for event in second.events
                if event.event_type == "cognition.completed"
            )
            second_trace = second_cognitive.data["understanding"]["mnn_signal"]
            self.assertEqual(second_trace["timestep"], 2)
            self.assertEqual(
                second_trace["snapshot"]["agent_id"],
                "machina-bridge-test",
            )
            self.assertTrue(restarted_brain.audit_cycle(second.cycle_id).valid)
            restarted_brain.store.verify_integrity()
            restarted_brain.close()

    def test_failed_outcome_is_recorded_as_negative_reward(self):
        class FailingExecutor:
            def execute(self, intent):
                raise RuntimeError("controlled failure")

        with tempfile.TemporaryDirectory() as directory:
            adapter = MNNOrganismCognitionAdapter(
                self.make_organism(),
                input_features={"sensor": "text_length"},
            )
            brain = VirtualBrain(
                Path(directory) / "brain.sqlite",
                cognition=adapter,
                action_executor=FailingExecutor(),
            )
            result = brain.run_cycle("Failure is observable.", "Record failure.")
            update = next(
                event.artifact
                for event in result.events
                if event.event_type == "mnn.plasticity_applied"
            )
            self.assertEqual(update.data["change"]["reward"], -1.0)
            self.assertEqual(
                update.data["change"]["validation_status"],
                "rejected",
            )
            self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
            brain.close()

    def test_invalid_feature_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            MNNOrganismCognitionAdapter(
                self.make_organism(),
                input_features={"sensor": "semantic_understanding"},
            )

    def test_zero_outcome_learning_rate_is_allowed(self):
        adapter = MNNOrganismCognitionAdapter(
            self.make_organism(),
            input_features={"sensor": "text_length"},
            outcome_learning_rate=0.0,
        )
        self.assertEqual(adapter.outcome_learning_rate, 0.0)


if __name__ == "__main__":
    unittest.main()
