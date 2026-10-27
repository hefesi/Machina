from __future__ import annotations

import json
import math
import unittest

from machina.self_model import SelfModel


class SelfModelTests(unittest.TestCase):
    def test_observation_without_evidence_defaults_to_unknown(self):
        model = SelfModel()
        state = model.update(
            {"tool_available": True, "runtime_mode": "offline"},
            cycle_id="cycle-1",
            evidence_refs={"tool_available": "runtime-check-1"},
        )
        self.assertEqual(state["beliefs"]["tool_available"]["status"], "observed")
        self.assertEqual(state["beliefs"]["tool_available"]["confidence"], 1.0)
        self.assertEqual(state["beliefs"]["runtime_mode"]["status"], "unknown")
        self.assertIsNone(state["beliefs"]["runtime_mode"]["value"])
        self.assertEqual(state["beliefs"]["runtime_mode"]["confidence"], 0.0)

    def test_inference_must_be_explicit(self):
        state = SelfModel().update(
            {"likely_failure": "network timeout"},
            cycle_id="cycle-2",
            statuses={"likely_failure": "inferred"},
            confidences={"likely_failure": 0.7},
        )
        belief = state["beliefs"]["likely_failure"]
        self.assertEqual(belief["status"], "inferred")
        self.assertEqual(belief["confidence"], 0.7)
        self.assertIsNone(belief["evidence_ref"])

    def test_observed_belief_requires_evidence(self):
        with self.assertRaisesRegex(ValueError, "requires evidence_ref"):
            SelfModel().update(
                {"tool_available": True}, cycle_id="cycle-1",
                statuses={"tool_available": "observed"},
            )

    def test_confidence_must_be_finite_and_bounded(self):
        for value in (-0.01, 1.01, math.nan, math.inf, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    SelfModel().update(
                        {"result": "ok"}, cycle_id="cycle-1",
                        evidence_refs={"result": "e-1"},
                        confidences={"result": value},
                    )

    def test_snapshot_round_trip_and_detachment(self):
        model = SelfModel()
        model.update(
            {"available": False}, cycle_id="cycle-7",
            evidence_refs={"available": "tool-state-7"},
            capability_estimates={
                "arithmetic": {
                    "estimate": {"success_rate": 0.9},
                    "confidence": 0.6, "status": "inferred",
                }
            },
            known_limitations=["No external network in this runtime"],
            resource_state={"memory_budget_mb": 512},
        )
        model.record_prediction_error({"prediction_ref": "pred-1", "error": 0.2})
        snapshot = model.snapshot()
        restored = SelfModel.from_snapshot(json.loads(json.dumps(snapshot)))
        self.assertEqual(restored.snapshot(), snapshot)
        snapshot["beliefs"]["available"]["value"] = True
        self.assertFalse(restored.beliefs["available"]["value"])

    def test_rejects_unknown_schema_and_malformed_snapshot(self):
        with self.assertRaisesRegex(ValueError, "unsupported"):
            SelfModel.from_snapshot({"schema_version": 99})
        state = SelfModel().update(
            {"ready": True}, cycle_id="cycle-1",
            evidence_refs={"ready": "check-1"},
        )
        state["beliefs"]["ready"]["confidence"] = 1.2
        with self.assertRaises(ValueError):
            SelfModel.from_snapshot(state)

    def test_unknown_belief_can_be_invalidated(self):
        model = SelfModel()
        model.update(
            {"ready": True}, cycle_id="cycle-1",
            evidence_refs={"ready": "check-1"},
        )
        belief = model.mark_unknown("ready", cycle_id="cycle-2")["beliefs"]["ready"]
        self.assertEqual(belief["status"], "unknown")
        self.assertIsNone(belief["value"])
        self.assertIsNone(belief["evidence_ref"])

    def test_prediction_errors_are_append_only(self):
        model = SelfModel()
        model.record_prediction_error({"prediction_ref": "p1", "error": 0.1})
        model.record_prediction_error({"prediction_ref": "p2", "error": 0.3})
        self.assertEqual([r["prediction_ref"] for r in model.prediction_errors], ["p1", "p2"])
        with self.assertRaisesRegex(ValueError, "requires prediction_ref and error"):
            model.record_prediction_error({"error": 0.2})

    def test_rejects_non_json_and_non_finite_observation_values(self):
        for value in (object(), math.nan, math.inf):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(ValueError):
                    SelfModel().update(
                        {"measurement": value}, cycle_id="cycle-1",
                        evidence_refs={"measurement": "sensor-1"},
                    )


if __name__ == "__main__":
    unittest.main()
