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
        self.assertEqual(("step:c1", "step:c2"), second.evidence_refs)

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
