import tempfile
import unittest
from pathlib import Path

from machina.event_store import EventStore
from machina.self_model import SelfModel
from machina.self_transformation import SelfTransformationTracker


class SelfTransformationTrackerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = EventStore(Path(self.tmp.name) / "events.sqlite3")
        self.store.create_cycle("cycle-2")
        self.tracker = SelfTransformationTracker(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_records_actual_self_change_with_evidence(self):
        before = SelfModel()
        after = SelfModel()
        after.update(
            {"runtime_available": True},
            cycle_id="cycle-2",
            evidence_refs={"runtime_available": "runtime-check-2"},
            capability_estimates={
                "planning": {
                    "estimate": {"success_rate": 0.75, "observations": 8},
                    "status": "inferred",
                    "confidence": 0.6,
                    "evidence_ref": "evaluation-8",
                }
            },
            known_limitations=["No autonomous external execution"],
        )
        result = self.tracker.record(
            before, after, cycle_id="cycle-2",
            trigger="evaluated planning outcomes",
            evidence_refs=["runtime-check-2", "evaluation-8"],
        )
        self.assertTrue(result["changed"])
        self.assertEqual("inferred", result["epistemic_status"])
        self.assertIn("capability_estimates", result["changes"])
        event = self.store.all_events()[0]
        self.assertEqual("self.transformed", event.event_type)
        self.assertEqual("MODEL_UPDATE", event.artifact.kind)
        self.assertEqual(["runtime-check-2", "evaluation-8"], event.artifact.data["evidence_refs"])

    def test_identical_snapshots_do_not_create_events(self):
        model = SelfModel()
        result = self.tracker.record(
            model, model.snapshot(), cycle_id="cycle-2",
            trigger="no-op", evidence_refs=[],
        )
        self.assertFalse(result["changed"])
        self.assertEqual([], self.store.all_events())

    def test_requires_valid_evidence_and_cycle(self):
        before, after = SelfModel(), SelfModel()
        after.update({"x": 1}, cycle_id="cycle-2")
        with self.assertRaises(ValueError):
            self.tracker.record(
                before, after, cycle_id="cycle-2",
                trigger="change", evidence_refs=[""],
            )
        with self.assertRaises(ValueError):
            self.tracker.record(
                before, after, cycle_id="missing",
                trigger="change", evidence_refs=[],
            )

    def test_journal_integrity_after_transformation(self):
        before, after = SelfModel(), SelfModel()
        after.update({"x": 1}, cycle_id="cycle-2")
        self.tracker.record(
            before, after, cycle_id="cycle-2",
            trigger="observation", evidence_refs=["sensor-1"],
        )
        self.store.verify_integrity()


if __name__ == "__main__":
    unittest.main()
