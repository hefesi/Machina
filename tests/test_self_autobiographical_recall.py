import tempfile
import unittest
from pathlib import Path

from machina.contracts import Artifact, ContractKind
from machina.event_store import EventStore
from machina.self_autobiography import SelfAutobiography
from machina.self_experience_integration import SelfExperienceIntegrator
from machina.self_autobiographical_recall import SelfAutobiographicalRecall


class SelfAutobiographicalRecallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = EventStore(Path(self.tmp.name) / "events.sqlite3")
        for cycle in ("c1", "c2", "c3"):
            self.store.create_cycle(cycle)
        self.integrator = SelfExperienceIntegrator(SelfAutobiography(self.store))
        self.recall = SelfAutobiographicalRecall(self.integrator)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def append(self, cycle, event_type, kind, data, refs=(), causation=None):
        artifact = Artifact.create(
            kind, cycle_id=cycle, producer="test", data=data,
            input_refs=refs, source_refs=refs, epistemic_status="inferred",
            confidence=0.8,
        )
        return self.store.append(event_type, artifact, causation_id=causation)

    def test_retrieves_transformation_with_explicit_experience_and_evidence(self):
        experience = self.append(
            "c1", "experience.recorded", ContractKind.EXPERIENCE,
            {"context": "Python reasoning task", "consequences": ["successful test"]},
        )
        transformed = self.append(
            "c2", "self.transformed", ContractKind.MODEL_UPDATE,
            {"change": {"trigger": "evaluation", "sections": {
                "capability_estimates": {
                    "previous": {"python_reasoning": 0.2},
                    "current": {"python_reasoning": 0.7},
                }}}, "evidence_refs": ["test-run:42"]},
            refs=["test-run:42"], causation=experience.event_id,
        )
        results = self.recall.recall("python reasoning successful test", limit=3)
        self.assertEqual(1, len(results))
        self.assertEqual(transformed.event_id, results[0].transformation_event_id)
        self.assertEqual(("capability_estimates.python_reasoning",), results[0].changed_paths)
        self.assertEqual(("test-run:42",), results[0].evidence_refs)
        self.assertEqual(experience.event_id, results[0].experience_records[0]["event_id"])
        self.store.verify_integrity()

    def test_does_not_invent_experience_links(self):
        self.append(
            "c1", "self.transformed", ContractKind.MODEL_UPDATE,
            {"change": {"trigger": "review", "sections": {
                "beliefs": {"previous": {"focus": "low"}, "current": {"focus": "high"}}
            }}, "evidence_refs": ["ev:1"]},
            refs=["ev:1"],
        )
        results = self.recall.recall("focus review")
        self.assertEqual(1, len(results))
        self.assertEqual((), results[0].experience_records)

    def test_no_match_and_input_validation(self):
        self.assertEqual((), self.recall.recall("unrelated query"))
        with self.assertRaises(ValueError):
            self.recall.recall(" ")
        with self.assertRaises(ValueError):
            self.recall.recall("query", limit=0)

    def test_read_only(self):
        self.append(
            "c1", "self.transformed", ContractKind.MODEL_UPDATE,
            {"change": {"trigger": "review", "sections": {
                "beliefs": {"previous": {"focus": "low"}, "current": {"focus": "high"}}
            }}, "evidence_refs": []},
        )
        before = len(self.store.all_events())
        self.recall.recall("focus review")
        self.assertEqual(before, len(self.store.all_events()))


if __name__ == "__main__":
    unittest.main()
