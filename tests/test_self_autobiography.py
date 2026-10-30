import tempfile
import unittest
from pathlib import Path

from machina.contracts import Artifact, ContractKind
from machina.event_store import EventStore
from machina.self_autobiography import SelfAutobiography


class SelfAutobiographyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = EventStore(Path(self.tmp.name) / "events.sqlite3")
        self.store.create_cycle("cycle-a")
        self.store.create_cycle("cycle-b")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def add_event(self, cycle, event_type, artifact_id, causation_id=None):
        artifact = Artifact.create(
            ContractKind.CYCLE_STATUS,
            cycle_id=cycle,
            producer="test",
            data={"status": event_type, "checkpoint": artifact_id},
            source_refs=("test-evidence",),
            epistemic_status="inferred",
            confidence=0.7,
            artifact_id=artifact_id,
        )
        return self.store.append(event_type, artifact, causation_id=causation_id)

    def test_reconstructs_chronology_and_causal_provenance(self):
        first = self.add_event("cycle-a", "cycle.started", "a1")
        self.add_event("cycle-a", "goal.selected", "a2", first.event_id)
        self.add_event("cycle-b", "cycle.started", "b1")
        view = SelfAutobiography(self.store)
        timeline = view.timeline()
        self.assertEqual(["cycle.started", "goal.selected", "cycle.started"],
                         [item["event_type"] for item in timeline])
        self.assertEqual(first.event_id, timeline[1]["causation_id"])
        self.assertEqual(["test-evidence"], timeline[0]["source_refs"])
        self.assertEqual("inferred", timeline[0]["epistemic_status"])

    def test_description_counts_and_filters(self):
        self.add_event("cycle-a", "cycle.started", "a1")
        self.add_event("cycle-a", "goal.selected", "a2")
        self.add_event("cycle-b", "cycle.started", "b1")
        view = SelfAutobiography(self.store)
        result = view.describe(cycle_id="cycle-a")
        self.assertEqual(2, result["record_count"])
        self.assertEqual({"cycle.started": 1, "goal.selected": 1}, result["event_type_counts"])
        self.assertEqual(2, len(view.timeline(event_types=["cycle.started"])))

    def test_limit_and_validation(self):
        self.add_event("cycle-a", "one", "a1")
        self.add_event("cycle-a", "two", "a2")
        view = SelfAutobiography(self.store)
        self.assertEqual(["two"], [item["event_type"] for item in view.timeline(limit=1)])
        with self.assertRaises(ValueError):
            view.timeline(limit=0)

    def test_projection_does_not_modify_journal(self):
        self.add_event("cycle-a", "cycle.started", "a1")
        before = [item.event_hash for item in self.store.all_events()]
        SelfAutobiography(self.store).describe()
        self.assertEqual(before, [item.event_hash for item in self.store.all_events()])
        self.store.verify_integrity()


if __name__ == "__main__":
    unittest.main()
