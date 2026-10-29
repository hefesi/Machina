from __future__ import annotations

import json
import unittest

from machina import MNNExperienceCycle
from machina.mnn import Connection, MNN, Unit
from machina.mnn_reward import RewardModulator


class MNNExperienceCycleTests(unittest.TestCase):
    def make_cycle(self) -> MNNExperienceCycle:
        network = MNN(weight_limit=2.0)
        network.add_unit(Unit("action", activation="identity"))
        # A constant bias keeps the postsynaptic unit active while the action
        # is present, making the intended pre/post co-activity explicit.
        network.add_unit(Unit("outcome", bias=1.0, activation="identity"))
        network.add_connection(Connection("action-outcome", "action", "outcome", 0.5))
        return MNNExperienceCycle(network, learning_rate=0.1)

    def test_delayed_outcome_updates_prior_eligible_connection(self):
        cycle = self.make_cycle()
        initial = cycle.network.connections["action-outcome"].weight
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})
        result = cycle.resolve(1.0)

        self.assertGreater(cycle.network.connections["action-outcome"].weight, initial)
        self.assertGreater(result["weight_changes"]["action-outcome"], 0.0)
        self.assertEqual(result["pending_steps"], 2)
        self.assertEqual(cycle.pending_steps, 0)
        self.assertEqual(cycle.modulator.eligibility, {})

    def test_neutral_steps_do_not_change_weights(self):
        cycle = self.make_cycle()
        initial = cycle.network.connections["action-outcome"].weight
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})
        self.assertEqual(cycle.network.connections["action-outcome"].weight, initial)

    def test_negative_outcome_reduces_prior_eligible_connection(self):
        cycle = self.make_cycle()
        initial = cycle.network.connections["action-outcome"].weight
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})
        cycle.resolve(-1.0)
        self.assertLess(cycle.network.connections["action-outcome"].weight, initial)

    def test_max_pending_steps_blocks_extra_steps_without_mutating_state(self):
        network = self.make_cycle().network
        cycle = MNNExperienceCycle(network, learning_rate=0.1, max_pending_steps=2)
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})
        snapshot = cycle.snapshot()
        weight = network.connections["action-outcome"].weight

        with self.assertRaisesRegex(RuntimeError, "max pending steps"):
            cycle.step({"action": 1.0})

        self.assertEqual(cycle.pending_steps, 2)
        self.assertEqual(cycle.snapshot(), snapshot)
        self.assertEqual(network.connections["action-outcome"].weight, weight)
        self.assertGreater(cycle.resolve(1.0)["weight_changes"]["action-outcome"], 0.0)

    def test_invalid_max_pending_steps_are_rejected(self):
        network = self.make_cycle().network
        for limit in (0, -1, True, 1.5, "2"):
            with self.subTest(limit=limit):
                with self.assertRaises(ValueError):
                    MNNExperienceCycle(network, max_pending_steps=limit)

    def test_max_pending_steps_survives_snapshot_and_legacy_loads(self):
        cycle = MNNExperienceCycle(
            self.make_cycle().network, learning_rate=0.1, max_pending_steps=3
        )
        cycle.step({"action": 1.0})
        snapshot = json.loads(json.dumps(cycle.snapshot()))
        restored = MNNExperienceCycle.from_snapshot(snapshot)
        self.assertEqual(restored.max_pending_steps, 3)
        self.assertEqual(restored.pending_steps, 1)

        legacy = {
            key: value
            for key, value in snapshot.items()
            if key != "max_pending_steps"
        }
        legacy_restored = MNNExperienceCycle.from_snapshot(legacy)
        self.assertIsNone(legacy_restored.max_pending_steps)
        self.assertEqual(legacy_restored.pending_steps, 1)

        snapshot["pending_steps"] = 4
        with self.assertRaisesRegex(ValueError, "cannot exceed max_pending_steps"):
            MNNExperienceCycle.from_snapshot(snapshot)

    def test_abort_discards_pending_traces_without_changing_weights(self):
        cycle = self.make_cycle()
        initial_weight = cycle.network.connections["action-outcome"].weight
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})

        result = cycle.abort()

        self.assertEqual(result["pending_steps"], 2)
        self.assertEqual(result["discarded_edges"], ["action-outcome"])
        self.assertEqual(
            cycle.network.connections["action-outcome"].weight, initial_weight
        )
        self.assertEqual(cycle.pending_steps, 0)
        self.assertEqual(cycle.modulator.eligibility, {})
        self.assertEqual(cycle.snapshot()["pending_steps"], 0)
        with self.assertRaises(RuntimeError):
            cycle.resolve(1.0)
        with self.assertRaises(RuntimeError):
            cycle.abort()

    def test_abort_preserves_the_reward_baseline(self):
        cycle = self.make_cycle()
        cycle.step({"action": 1.0})
        cycle.resolve(1.0)
        baseline = cycle.modulator.baseline
        cycle.step({"action": 1.0})

        cycle.abort()

        self.assertEqual(cycle.modulator.baseline, baseline)
        self.assertIsNotNone(cycle.modulator.baseline)

    def test_snapshot_restores_in_flight_experience(self):
        cycle = self.make_cycle()
        cycle.step({"action": 1.0})
        cycle.step({"action": 0.0})
        restored = MNNExperienceCycle.from_snapshot(json.loads(json.dumps(cycle.snapshot())))

        self.assertEqual(restored.pending_steps, 2)
        self.assertEqual(restored.snapshot(), cycle.snapshot())
        result = restored.resolve(1.0)
        self.assertGreater(result["weight_changes"]["action-outcome"], 0.0)

    def test_cannot_resolve_without_pending_experience(self):
        with self.assertRaises(RuntimeError):
            self.make_cycle().resolve(1.0)

    def test_non_finite_reward_is_rejected_without_closing_experience(self):
        cycle = self.make_cycle()
        cycle.step({"action": 1.0})
        with self.assertRaises(ValueError):
            cycle.resolve(float("nan"))
        self.assertEqual(cycle.pending_steps, 1)

    def test_invalid_snapshots_are_rejected(self):
        valid = self.make_cycle().snapshot()
        cases = {
            "not a mapping": [],
            "missing fields": {"schema_version": 1},
            "unknown field": {**valid, "extra": 1},
            "boolean pending steps": {**valid, "pending_steps": True},
            "negative pending steps": {**valid, "pending_steps": -1},
            "non-mapping network": {**valid, "network": []},
            "non-mapping modulator": {**valid, "modulator": []},
        }
        for label, snapshot in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    MNNExperienceCycle.from_snapshot(snapshot)

    def test_closed_snapshot_cannot_retain_eligibility_traces(self):
        cycle = self.make_cycle()
        cycle.step({"action": 1.0})
        snapshot = cycle.snapshot()
        snapshot["pending_steps"] = 0
        with self.assertRaisesRegex(ValueError, "closed experience"):
            MNNExperienceCycle.from_snapshot(snapshot)

    def test_snapshot_rejects_unknown_eligibility_edge(self):
        cycle = self.make_cycle()
        cycle.step({"action": 1.0})
        snapshot = cycle.snapshot()
        snapshot["modulator"]["eligibility"] = {"missing-edge": 0.5}
        snapshot["pending_steps"] = 1
        with self.assertRaisesRegex(ValueError, "unknown edges"):
            MNNExperienceCycle.from_snapshot(snapshot)

    def test_invalid_construction_parameters_are_rejected(self):
        network = self.make_cycle().network
        for rate in (-1, float("nan"), float("inf"), True):
            with self.subTest(rate=rate):
                with self.assertRaises(ValueError):
                    MNNExperienceCycle(network, learning_rate=rate)
        with self.assertRaises(ValueError):
            MNNExperienceCycle("not a network")
        with self.assertRaises(ValueError):
            MNNExperienceCycle(network, modulator="not a modulator")

    def test_modulator_snapshot_requires_explicit_fields(self):
        modulator = RewardModulator()
        with self.assertRaisesRegex(ValueError, "missing fields"):
            RewardModulator.from_snapshot({"schema_version": 1})
        snapshot = modulator.snapshot()
        snapshot["extra"] = 1
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            RewardModulator.from_snapshot(snapshot)


if __name__ == "__main__":
    unittest.main()
