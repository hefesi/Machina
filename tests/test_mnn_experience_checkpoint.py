from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from machina import ActivityGrowthPolicy
from machina.mnn import Connection, MNN, Unit
from machina.mnn_experience import MNNExperienceCheckpointStore, MNNExperienceCycle


class MNNExperienceCheckpointTests(unittest.TestCase):
    def make_cycle(self) -> MNNExperienceCycle:
        network = MNN(weight_limit=2.0)
        network.add_unit(Unit("action", activation="identity"))
        network.add_unit(Unit("outcome", bias=1.0, activation="identity"))
        network.add_connection(
            Connection("action-outcome", "action", "outcome", 0.5)
        )
        return MNNExperienceCycle(network, learning_rate=0.1)

    def test_round_trip_preserves_in_flight_experience(self):
        with tempfile.TemporaryDirectory() as directory:
            cycle = self.make_cycle()
            cycle.step({"action": 1.0})
            expected = cycle.snapshot()

            store = MNNExperienceCheckpointStore(
                Path(directory) / "nested" / "experience.json"
            )
            store.save(cycle)
            restored = store.load()

            self.assertEqual(restored.snapshot(), expected)
            self.assertEqual(restored.pending_steps, 1)

    def test_pending_outcome_survives_restart_and_applies_once(self):
        with tempfile.TemporaryDirectory() as directory:
            cycle = self.make_cycle()
            cycle.step({"action": 1.0})
            cycle.step({"action": 0.0})
            initial_weight = cycle.network.connections["action-outcome"].weight

            store = MNNExperienceCheckpointStore(Path(directory) / "experience.json")
            store.save(cycle)

            restored = store.load()
            result = restored.resolve(1.0)

            self.assertEqual(result["pending_steps"], 2)
            self.assertGreater(
                restored.network.connections["action-outcome"].weight,
                initial_weight,
            )
            self.assertEqual(restored.modulator.eligibility, {})
            self.assertEqual(restored.pending_steps, 0)

            store.save(restored)
            reopened = store.load()
            self.assertEqual(reopened.pending_steps, 0)
            self.assertEqual(reopened.modulator.eligibility, {})
            with self.assertRaises(RuntimeError):
                reopened.resolve(1.0)

    def test_checkpoint_preserves_pending_step_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            cycle = MNNExperienceCycle(
                self.make_cycle().network,
                learning_rate=0.1,
                max_pending_steps=1,
            )
            cycle.step({"action": 1.0})
            store = MNNExperienceCheckpointStore(Path(directory) / "experience.json")
            store.save(cycle)

            restored = store.load()
            self.assertEqual(restored.max_pending_steps, 1)
            self.assertEqual(restored.pending_steps, 1)
            with self.assertRaisesRegex(RuntimeError, "max pending steps"):
                restored.step({"action": 1.0})

    def test_checkpoint_preserves_growth_policy_for_delayed_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            network = MNN(weight_limit=2.0)
            network.add_unit(Unit("cue", activation="identity"))
            network.add_unit(Unit("response", activation="identity"))
            policy = ActivityGrowthPolicy(
                max_new_connections=1,
                initial_weight=0.75,
                allowed_sources={"cue"},
                allowed_targets={"response"},
            )
            cycle = MNNExperienceCycle(
                network,
                learning_rate=0.1,
                growth_policy=policy,
            )
            cycle.step({"cue": 1.0, "response": 1.0})
            store = MNNExperienceCheckpointStore(Path(directory) / "experience.json")
            store.save(cycle)

            restored = store.load()
            self.assertIsNotNone(restored.growth_policy)
            result = restored.resolve(1.0)

            self.assertEqual(len(result["grown_connections"]), 1)
            self.assertIn("grown:cue->response", restored.network.connections)

    def test_checkpoint_preserves_structural_utility_across_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            network = MNN(weight_limit=2.0)
            network.add_unit(Unit("cue", activation="identity"))
            network.add_unit(Unit("response", activation="identity"))
            policy = ActivityGrowthPolicy(
                max_new_connections=1,
                initial_weight=0.75,
                allowed_sources={"cue"},
                allowed_targets={"response"},
            )
            cycle = MNNExperienceCycle(
                network,
                learning_rate=0.1,
                growth_policy=policy,
                prune_after_negative_outcomes=2,
            )
            edge_id = "grown:cue->response"
            cycle.step({"cue": 1.0, "response": 1.0})
            cycle.resolve(1.0)
            cycle.step({"cue": 1.0, "response": 1.0})
            cycle.resolve(-1.0)
            store = MNNExperienceCheckpointStore(Path(directory) / "experience.json")
            store.save(cycle)

            restored = store.load()
            self.assertEqual(restored.structural_utility, {edge_id: -1})
            restored.step({"cue": 1.0, "response": 1.0})
            result = restored.resolve(-1.0)
            self.assertEqual(result["pruned_connections"], [edge_id])
            self.assertNotIn(edge_id, restored.network.connections)

    def test_invalid_checkpoint_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken.json"
            store = MNNExperienceCheckpointStore(path)

            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid MNN experience checkpoint JSON"):
                store.load()

            path.write_text("[]", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must contain a JSON object"):
                store.load()

            path.write_text(json.dumps({"schema_version": 999}), encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, "unsupported MNN experience-cycle snapshot schema"
            ):
                store.load()

            path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing fields"):
                store.load()

    def test_save_rejects_non_cycle_values(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MNNExperienceCheckpointStore(Path(directory) / "experience.json")
            with self.assertRaisesRegex(ValueError, "must be an MNNExperienceCycle"):
                store.save("not a cycle")
            self.assertFalse(store.path.exists())


if __name__ == "__main__":
    unittest.main()
