import tempfile
import unittest
from pathlib import Path

from machina.contracts import Artifact, ContractKind, EpistemicStatus
from machina.event_store import EventStore
from machina.fragment_memory import FragmentMemory
from machina.mnn_event_memory_projector import MNNEventMemoryProjector

class MNNEventMemoryProjectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = EventStore(root / "events.db")
        self.memory = FragmentMemory(root / "memory.db")
        self.addCleanup(self.store.close)
        self.addCleanup(self.memory.close)
        self.store.create_cycle("cycle-projector")
        first_artifact = Artifact.create(ContractKind.OBSERVATION,
            cycle_id="cycle-projector", producer="test",
            data={"content": "observation", "source": {"id": "source-1"},
                  "modality": "text", "observed_at": "2026-10-30T00:00:00+00:00",
                  "reliability": 1.0}, epistemic_status=EpistemicStatus.OBSERVED)
        self.first = self.store.append("perception.observed", first_artifact)
        second_artifact = Artifact.create(ContractKind.GOAL,
            cycle_id="cycle-projector", producer="test",
            data={"description": "goal", "priority": 1, "constraints": [],
                  "success_criteria": []}, input_refs=[first_artifact.id],
            epistemic_status=EpistemicStatus.INTERPRETED)
        self.second = self.store.append("goal.created", second_artifact,
            causation_id=self.first.artifact.id)
        self.projector = MNNEventMemoryProjector(self.store, self.memory)

    def test_projects_events_with_provenance_and_causal_metadata(self):
        result = self.projector.project()
        self.assertEqual(2, result.scanned_count)
        self.assertEqual(2, result.projected_count)
        self.assertEqual(self.second.sequence, result.last_sequence)
        fragment = self.memory.get("event_" + self.second.event_id, record_access=False)
        self.assertEqual("episodic_event", fragment.kind)
        self.assertEqual(self.second.artifact.id, fragment.metadata["artifact_id"])
        self.assertEqual(self.first.artifact.id, fragment.metadata["causation_id"])
        self.assertEqual(self.second.event_hash, fragment.metadata["event_hash"])

    def test_replay_is_idempotent(self):
        first = self.projector.project()
        second = self.projector.project()
        self.assertEqual(2, first.projected_count)
        self.assertEqual(0, second.projected_count)
        self.assertEqual(2, second.already_projected_count)
        self.assertEqual(2, self.memory.count())

    def test_cursor_and_limit_allow_resumable_batches(self):
        first = self.projector.project(limit=1)
        self.assertEqual(self.first.sequence, first.last_sequence)
        second = self.projector.project(after_sequence=first.last_sequence)
        self.assertEqual(1, second.projected_count)
        self.assertEqual(self.second.sequence, second.last_sequence)

    def test_event_type_filter_advances_cursor_for_scanned_events(self):
        result = self.projector.project(event_types={"goal.created"})
        self.assertEqual(2, result.scanned_count)
        self.assertEqual(1, result.projected_count)
        self.assertEqual(self.second.sequence, result.last_sequence)
        self.assertEqual(1, self.memory.count())

    def test_invalid_cursor_limit_and_filter_are_rejected(self):
        with self.assertRaises(ValueError):
            self.projector.project(after_sequence=-1)
        with self.assertRaises(ValueError):
            self.projector.project(limit=0)
        with self.assertRaises(ValueError):
            self.projector.project(event_types={" "})

if __name__ == "__main__":
    unittest.main()
