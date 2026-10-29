from __future__ import annotations

import json
import unittest

from machina import ActivityGrowthPolicy, MNNExperienceCycle
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

    def make_growth_cycle(
        self,
        *,
        growth_min_reward: float = 0.0,
        prune_after_negative_outcomes: int | None = None,
    ) -> MNNExperienceCycle:
        network = MNN(weight_limit=2.0)
        network.add_unit(Unit("cue", activation="identity"))
        network.add_unit(Unit("response", activation="identity"))
        policy = ActivityGrowthPolicy(
            max_new_connections=1,
            initial_weight=0.75,
            min_activity=0.1,
            allowed_sources={"cue"},
            allowed_targets={"response"},
        )
        return MNNExperienceCycle(
            network,
            learning_rate=0.1,
            growth_policy=policy,
            growth_min_reward=growth_min_reward,
            prune_after_negative_outcomes=prune_after_negative_outcomes,
        )

    def test_positive_outcome_can_grow_connections(self):
        cycle = self.make_growth_cycle()
        cycle.step({"cue": 1.0, "response": 1.0})

        result = cycle.resolve(1.0)

        self.assertEqual(len(result["grown_connections"]), 1)
        grown = result["grown_connections"][0]
        self.assertEqual(grown["source"], "cue")
        self.assertEqual(grown["target"], "response")
        self.assertEqual(grown["weight"], 0.75)
        self.assertIn(grown["id"], cycle.network.connections)
        self.assertEqual(
            [edge["id"] for edge in result["network_snapshot"]["connections"]],
            [grown["id"]],
        )

    def test_negative_outcome_does_not_grow_connections(self):
        cycle = self.make_growth_cycle()
        cycle.step({"cue": 1.0, "response": 1.0})

        result = cycle.resolve(-1.0)

        self.assertEqual(result["grown_connections"], [])
        self.assertEqual(cycle.network.connections, {})

    def test_growth_threshold_and_abort_are_respected(self):
        cycle = self.make_growth_cycle(growth_min_reward=0.5)
        cycle.step({"cue": 1.0, "response": 1.0})
        result = cycle.resolve(0.25)
        self.assertEqual(result["grown_connections"], [])

        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.abort()
        self.assertEqual(cycle.network.connections, {})

    def test_grown_connection_is_pruned_after_repeated_negative_outcomes(self):
        cycle = self.make_growth_cycle(prune_after_negative_outcomes=2)
        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.resolve(1.0)
        edge_id = "grown:cue->response"
        self.assertEqual(cycle.structural_utility, {edge_id: 0})

        cycle.step({"cue": 1.0, "response": 1.0})
        first_failure = cycle.resolve(-1.0)
        self.assertEqual(first_failure["pruned_connections"], [])
        self.assertEqual(cycle.structural_utility, {edge_id: -1})
        self.assertIn(edge_id, cycle.network.connections)

        cycle.step({"cue": 1.0, "response": 1.0})
        second_failure = cycle.resolve(-1.0)
        self.assertEqual(second_failure["pruned_connections"], [edge_id])
        self.assertNotIn(edge_id, cycle.network.connections)
        self.assertEqual(cycle.structural_utility, {})
        self.assertEqual(cycle.modulator.eligibility, {})

    def test_positive_outcome_resets_grown_connection_utility(self):
        cycle = self.make_growth_cycle(prune_after_negative_outcomes=2)
        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.resolve(1.0)
        edge_id = "grown:cue->response"

        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.resolve(-1.0)
        self.assertEqual(cycle.structural_utility[edge_id], -1)

        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.resolve(1.0)
        self.assertEqual(cycle.structural_utility[edge_id], 0)

        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.resolve(-1.0)
        self.assertIn(edge_id, cycle.network.connections)
        self.assertEqual(cycle.structural_utility[edge_id], -1)

    def test_structural_utility_survives_snapshot(self):
        cycle = self.make_growth_cycle(prune_after_negative_outcomes=2)
        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.resolve(1.0)
        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.resolve(-1.0)
        edge_id = "grown:cue->response"

        snapshot = json.loads(json.dumps(cycle.snapshot()))
        restored = MNNExperienceCycle.from_snapshot(snapshot)

        self.assertEqual(restored.prune_after_negative_outcomes, 2)
        self.assertEqual(restored.structural_utility, {edge_id: -1})
        restored.step({"cue": 1.0, "response": 1.0})
        result = restored.resolve(-1.0)
        self.assertEqual(result["pruned_connections"], [edge_id])
        self.assertNotIn(edge_id, restored.network.connections)

    def test_growth_policy_survives_snapshot_and_legacy_loads(self):
        cycle = self.make_growth_cycle()
        cycle.step({"cue": 1.0, "response": 1.0})
        snapshot = json.loads(json.dumps(cycle.snapshot()))
        restored = MNNExperienceCycle.from_snapshot(snapshot)

        self.assertIsNotNone(restored.growth_policy)
        result = restored.resolve(1.0)
        self.assertEqual(len(result["grown_connections"]), 1)

        legacy = {
            key: value
            for key, value in snapshot.items()
            if key not in {
                "growth_policy",
                "growth_min_reward",
                "prune_after_negative_outcomes",
                "structural_utility",
            }
        }
        legacy_restored = MNNExperienceCycle.from_snapshot(legacy)
        self.assertIsNone(legacy_restored.growth_policy)
        self.assertEqual(legacy_restored.growth_min_reward, 0.0)
        self.assertIsNone(legacy_restored.prune_after_negative_outcomes)
        self.assertEqual(legacy_restored.structural_utility, {})

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
            "non-mapping structural utility": {**valid, "structural_utility": []},
            "boolean structural utility": {
                **valid,
                "structural_utility": {"action-outcome": True},
            },
            "positive structural utility": {
                **valid,
                "structural_utility": {"action-outcome": 1},
            },
            "unknown structural utility edge": {
                **valid,
                "structural_utility": {"missing": -1},
            },
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

    def test_snapshot_rejects_utility_that_should_have_been_pruned(self):
        cycle = self.make_growth_cycle(prune_after_negative_outcomes=2)
        cycle.step({"cue": 1.0, "response": 1.0})
        cycle.resolve(1.0)
        snapshot = cycle.snapshot()
        snapshot["structural_utility"] = {"grown:cue->response": -2}
        with self.assertRaisesRegex(ValueError, "should have been pruned"):
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
        with self.assertRaises(ValueError):
            MNNExperienceCycle(network, growth_policy="not a policy")
        for threshold in (True, float("nan"), float("inf"), "high"):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    MNNExperienceCycle(network, growth_min_reward=threshold)
        for prune_after in (0, -1, True, 1.5, "2"):
            with self.subTest(prune_after=prune_after):
                with self.assertRaises(ValueError):
                    MNNExperienceCycle(
                        network,
                        prune_after_negative_outcomes=prune_after,
                    )
        with self.assertRaisesRegex(ValueError, "requires a growth_policy"):
            MNNExperienceCycle(
                network,
                prune_after_negative_outcomes=1,
            )

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
