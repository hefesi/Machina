import unittest

from machina.self_model import SelfModel
from machina.homeostasis import HomeostaticRegulator, HomeostaticRule


class HomeostaticRegulatorTests(unittest.TestCase):
    def setUp(self):
        self.model = SelfModel()
        self.rule = HomeostaticRule(
            "internal.mnn.prediction_error", "error_recovery",
            lower=0.1, upper=0.4, below_adjustment=-0.05,
            above_adjustment=0.12,
        )
        self.regulator = HomeostaticRegulator(
            self.model, {"prediction_error": self.rule}, persistence_cycles=2
        )

    def observe(self, cycle, value, status="observed"):
        kwargs = {"cycle_id": cycle}
        if status == "observed":
            kwargs["evidence_refs"] = {"internal.mnn.prediction_error": f"step:{cycle}"}
        else:
            kwargs["statuses"] = {"internal.mnn.prediction_error": status}
        self.model.update({"internal.mnn.prediction_error": value}, **kwargs)

    def test_requires_persistent_deviation_before_proposing(self):
        self.observe("c1", 0.8)
        first = self.regulator.assess()
        self.assertEqual({}, first.adjustments)
        self.assertEqual(1, first.persistence["prediction_error"])
        self.observe("c2", 0.9)
        second = self.regulator.assess()
        self.assertEqual({"error_recovery": 0.12}, second.adjustments)
        self.assertEqual(("step:c2",), second.evidence_refs)

    def test_in_range_observation_resets_persistence(self):
        self.observe("c1", 0.8)
        self.regulator.assess()
        self.observe("c2", 0.3)
        result = self.regulator.assess()
        self.assertEqual({}, result.adjustments)
        self.assertEqual(0, result.persistence["prediction_error"])

    def test_direction_change_restarts_persistence(self):
        self.observe("c1", 0.8)
        self.regulator.assess()
        self.observe("c2", 0.0)
        result = self.regulator.assess()
        self.assertEqual({}, result.adjustments)
        self.assertEqual(1, result.persistence["prediction_error"])

    def test_unknown_telemetry_resets_without_guessing(self):
        self.observe("c1", 0.8)
        self.regulator.assess()
        self.observe("c2", None, status="unknown")
        result = self.regulator.assess()
        self.assertEqual({}, result.adjustments)
        self.assertEqual((), result.evidence_refs)

    def test_multiple_rules_for_one_drive_aggregate_order_independently(self):
        low_metric = HomeostaticRule(
            "metric.low", "memory",
            lower=0.2, upper=0.8,
            below_adjustment=0.2, above_adjustment=-0.1,
        )
        high_metric = HomeostaticRule(
            "metric.high", "memory",
            lower=0.2, upper=0.8,
            below_adjustment=0.1, above_adjustment=-0.05,
        )
        observations = {
            "metric.low": 0.1,
            "metric.high": 0.9,
        }
        evidence = {
            "metric.low": "telemetry:low",
            "metric.high": "telemetry:high",
        }

        def assess(rules):
            model = SelfModel()
            model.update(
                observations,
                cycle_id="multi-metric-cycle",
                evidence_refs=evidence,
                statuses={name: "observed" for name in observations},
            )
            regulator = HomeostaticRegulator(
                model, rules, persistence_cycles=1
            )
            return regulator.assess().adjustments

        forward = assess({"low": low_metric, "high": high_metric})
        reverse = assess({"high": high_metric, "low": low_metric})
        self.assertAlmostEqual(0.15, forward["memory"])
        self.assertAlmostEqual(forward["memory"], reverse["memory"])
        self.assertEqual(set(forward), set(reverse))

    def test_saturated_drive_aggregation_is_order_independent(self):
        low_a = HomeostaticRule(
            "metric.low_a", "memory",
            lower=0.2, upper=0.8,
            below_adjustment=0.3, above_adjustment=-0.3,
        )
        low_b = HomeostaticRule(
            "metric.low_b", "memory",
            lower=0.2, upper=0.8,
            below_adjustment=0.3, above_adjustment=-0.3,
        )
        high = HomeostaticRule(
            "metric.high", "memory",
            lower=0.2, upper=0.8,
            below_adjustment=0.3, above_adjustment=-0.3,
        )
        observations = {
            "metric.low_a": 0.1,
            "metric.low_b": 0.1,
            "metric.high": 0.9,
        }
        evidence = {
            "metric.low_a": "telemetry:low-a",
            "metric.low_b": "telemetry:low-b",
            "metric.high": "telemetry:high",
        }

        def assess(rules):
            model = SelfModel()
            model.update(
                observations,
                cycle_id="saturated-multi-metric-cycle",
                evidence_refs=evidence,
                statuses={name: "observed" for name in observations},
            )
            regulator = HomeostaticRegulator(
                model, rules, persistence_cycles=1
            )
            return regulator.assess().adjustments

        forward = assess({"low_a": low_a, "low_b": low_b, "high": high})
        reverse = assess({"high": high, "low_b": low_b, "low_a": low_a})
        self.assertAlmostEqual(0.3, forward["memory"])
        self.assertAlmostEqual(forward["memory"], reverse["memory"])
        self.assertEqual(set(forward), set(reverse))

    def test_snapshot_restores_temporal_state(self):
        self.observe("c1", 0.8)
        self.regulator.assess()
        restored = HomeostaticRegulator.from_snapshot(self.model, self.regulator.snapshot())
        self.observe("c2", 0.9)
        result = restored.assess()
        self.assertEqual({"error_recovery": 0.12}, result.adjustments)

    def test_assessment_is_read_only_and_cycle_is_idempotency_guarded(self):
        self.observe("c1", 0.8)
        before = self.model.snapshot()
        self.regulator.assess()
        self.assertEqual(before, self.model.snapshot())
        with self.assertRaises(ValueError):
            self.regulator.assess(cycle_id="c1")

    def test_rejects_invalid_rules(self):
        with self.assertRaises(ValueError):
            HomeostaticRule("metric", "drive", 0.5, 0.5, 0.0, 0.1)
        with self.assertRaises(ValueError):
            HomeostaticRule("metric", "drive", 0.1, 0.5, 0.0, 0.4)


if __name__ == "__main__":
    unittest.main()
