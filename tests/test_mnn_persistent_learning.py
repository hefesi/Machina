from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_persistent_learning import make_network, run_benchmark
from machina.mnn_checkpoint import MNNCheckpointStore


class MNNCheckpointTests(unittest.TestCase):
    def test_checkpoint_round_trip_preserves_topology_weights_and_state(self):
        with tempfile.TemporaryDirectory() as directory:
            network = make_network()
            network.step({"context_positive": 1.0})
            network.apply_hebbian(learning_rate=0.3, reward=1.0)
            expected = network.snapshot()

            store = MNNCheckpointStore(Path(directory) / "nested" / "network.json")
            store.save(network)
            restored = store.load()

            self.assertEqual(restored.snapshot(), expected)

    def test_trained_behavior_survives_checkpoint_and_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark(checkpoint_path=Path(directory) / "learned.json")
            self.assertTrue(result["passed"], result)
            self.assertEqual(0.5, result["baseline_fixed_weights"]["accuracy"])
            self.assertEqual(1.0, result["trained_before_restart"]["accuracy"])
            self.assertEqual(1.0, result["restored_after_restart"]["accuracy"])
            self.assertTrue(result["weights_preserved"])
            self.assertEqual(result["trained_weights"], result["restored_weights"])

    def test_invalid_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid MNN checkpoint JSON"):
                MNNCheckpointStore(path).load()

            path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unsupported MNN snapshot schema"):
                MNNCheckpointStore(path).load()

    def test_invalid_training_parameters_are_rejected(self):
        with self.assertRaises(ValueError):
            run_benchmark(training_rounds=0)
        with self.assertRaises(ValueError):
            run_benchmark(learning_rate=-0.1)


if __name__ == "__main__":
    unittest.main()
