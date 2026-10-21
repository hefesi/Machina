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
        network.add_unit(Unit("signal", activation="tanh"))
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
            self.assertTrue(brain.audit_cycle(result.cycle_id).valid)
            brain.store.verify_integrity()
            brain.close()

    def test_adapter_rejects_unknown_units_and_features(self):
        network = self.make_network()
        with self.assertRaises(ValueError):
            MNNCognitionAdapter(network, input_features={"missing": "text_length"})
        with self.assertRaises(ValueError):
            MNNCognitionAdapter(network, input_features={"text": "semantic_understanding"})


if __name__ == "__main__":
    unittest.main()
