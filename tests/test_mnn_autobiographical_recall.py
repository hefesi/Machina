import tempfile
import unittest
from pathlib import Path

from machina.contracts import Artifact, ContractKind, EpistemicStatus
from machina.event_store import EventStore
from machina.fragment_memory import FragmentMemory
from machina.mnn_autobiographical_recall import MNNAutobiographicalRecall
from machina.mnn_event_memory_projector import MNNEventMemoryProjector


class MNNAutobiographicalRecallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = EventStore(root / "events.db")
        self.memory = FragmentMemory(root / "memory.db")
        self.addCleanup(self.store.close)
        self.addCleanup(self.memory.close)
        self.store.create_cycle("cycle-recall")
        artifact = Artifact.create(
            ContractKind.OBSERVATION,
            cycle_id="cycle-recall",
            producer="test",
            data={
                "content": "robot detected overheating in motor assembly",
                "source": {"id": "sensor-1"},
                "modality": "text",
                "observed_at": "2026-10-30T00:00:00+00:00",
                "reliability": 1.0,
            },
            epistemic_status=EpistemicStatus.OBSERVED,
        )
        self.event = self.store.append("perception.observed", artifact)
        self.projector = MNNEventMemoryProjector(self.store, self.memory)
        self.projector.project()
        self.recall_service = MNNAutobiographicalRecall(self.memory)

    def test_recalls_event_and_preserves_source_provenance(self):
        episodes = self.recall_service.recall("overheating motor")
        self.assertEqual(1, len(episodes))
        episode = episodes[0]
        self.assertEqual(self.event.event_id, episode.event_id)
        self.assertEqual(self.event.event_hash, episode.event_hash)
        self.assertEqual(self.event.artifact.id, episode.artifact_id)
        self.assertEqual(self.event.sequence, episode.sequence)
        self.assertEqual("perception.observed", episode.event_type)
        self.assertEqual("robot detected overheating in motor assembly", episode.artifact["data"]["content"])

    def test_excludes_non_event_fragments_even_when_they_match(self):
        self.memory.add(
            "overheating motor incident notes",
            kind="note",
            source_uri="test://note/1",
        )
        episodes = self.recall_service.recall("overheating motor")
        self.assertEqual(1, len(episodes))
        self.assertEqual(self.event.event_id, episodes[0].event_id)

    def test_context_and_limit_are_forwarded_to_retrieval(self):
        episodes = self.recall_service.recall(
            "overheating motor", limit=1, context="maintenance"
        )
        self.assertEqual(1, len(episodes))

    def test_invalid_query_and_limit_are_rejected(self):
        with self.assertRaises(ValueError):
            self.recall_service.recall(" ")
        with self.assertRaises(ValueError):
            self.recall_service.recall("motor", limit=0)
        with self.assertRaises(ValueError):
            self.memory.recall("motor", kinds="episodic_event")


if __name__ == "__main__":
    unittest.main()
