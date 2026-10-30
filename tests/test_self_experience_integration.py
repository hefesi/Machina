import tempfile
import unittest
from pathlib import Path

from machina.contracts import Artifact, ContractKind
from machina.event_store import EventStore
from machina.self_autobiography import SelfAutobiography
from machina.self_experience_integration import SelfExperienceIntegrator


class SelfExperienceIntegratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = EventStore(Path(self.tmp.name) / "events.sqlite3")
        for cycle in ("c1", "c2", "c3", "c4"):
            self.store.create_cycle(cycle)
        self.view = SelfAutobiography(self.store)
        self.integrator = SelfExperienceIntegrator(self.view)

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

    def transform(self, cycle, previous, current, refs, causation=None):
        return self.append(
            cycle, "self.transformed", ContractKind.MODEL_UPDATE,
            {"target": "SelfModel", "previous_version": "old", "new_version": cycle,
             "change": {"trigger": "evaluation", "sections": {
                 "capability_estimates": {"previous": previous, "current": current}}},
             "evidence_refs": list(refs), "reason": "test", "created_by": "test"},
            refs, causation,
        )

    def test_links_only_explicit_causation_and_references(self):
        experience = self.append(
            "c1", "experience.recorded", ContractKind.EXPERIENCE,
            {"context": "task", "observation_refs": [], "action_intent_ref": "intent",
             "action_result_ref": "result", "expected_outcome": 1, "actual_outcome": 1,
             "prediction_error": 0, "consequences": [], "occurred_at": "now"},
        )
        transformed = self.transform(
            "c2", {"reasoning": 0.2}, {"reasoning": 0.4}, [],
            causation=experience.event_id,
        )
        result = self.integrator.trace(transformed.event_id)
        self.assertEqual(experience.event_id, result["experience_links"][0]["event_id"])
        self.assertEqual("explicit_causation", result["experience_links"][0]["link_basis"])

    def test_reinforcement_and_reversal_are_distinguished(self):
        first = self.transform("c1", {"reasoning": 0.2}, {"reasoning": 0.4}, ["e1"])
        self.transform("c2", {"reasoning": 0.1}, {"reasoning": 0.4}, ["e2"])
        result = self.integrator.trace(first.event_id)
        self.assertEqual("reinforced", result["durability"]["capability_estimates.reasoning"]["status"])

        reversed_event = self.transform("c3", {"reasoning": 0.4}, {"reasoning": 0.1}, ["e3"])
        result = self.integrator.trace(first.event_id)
        self.assertEqual("reversed", result["durability"]["capability_estimates.reasoning"]["status"])
        self.assertIsNotNone(self.integrator.trace(reversed_event.event_id))

    def test_single_observation_is_not_claimed_persistent(self):
        event = self.transform("c1", {"reasoning": 0.2}, {"reasoning": 0.4}, ["e1"])
        result = self.integrator.trace(event.event_id)
        self.assertEqual("observed_once", result["durability"]["capability_estimates.reasoning"]["status"])

    def test_projection_is_read_only_and_integrity_remains_valid(self):
        self.transform("c1", {"reasoning": 0.2}, {"reasoning": 0.4}, ["e1"])
        before = len(self.store.all_events())
        self.integrator.integrate()
        self.assertEqual(before, len(self.store.all_events()))
        self.store.verify_integrity()

    def test_unknown_causation_does_not_create_link(self):
        event = self.transform("c1", {"reasoning": 0.2}, {"reasoning": 0.4}, [], "missing-event")
        result = self.integrator.trace(event.event_id)
        self.assertEqual([], result["experience_links"])
        self.assertIn(event.event_id, self.integrator.integrate()["unlinked_transformations"])


if __name__ == "__main__":
    unittest.main()
