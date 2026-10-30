import tempfile
import unittest
from pathlib import Path

from machina.contracts import Artifact, ContractKind
from machina.event_store import EventStore
from machina.self_autobiography import SelfAutobiography
from machina.self_experience_integration import SelfExperienceIntegrator
from machina.self_influence import SelfInfluenceAdapter


class SelfInfluenceAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = EventStore(Path(self.tmp.name) / "events.sqlite3")
        for cycle in ("c1", "c2", "c3"):
            self.store.create_cycle(cycle)
        self.adapter = SelfInfluenceAdapter(
            SelfExperienceIntegrator(SelfAutobiography(self.store)),
            {"capability_estimates.reasoning": "self_reasoning"},
        )

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def transform(self, cycle, before, after, refs):
        artifact = Artifact.create(
            ContractKind.MODEL_UPDATE, cycle_id=cycle, producer="test",
            data={"target": "SelfModel", "previous_version": "old",
                  "new_version": cycle,
                  "change": {"trigger": "evaluation", "sections": {
                      "capability_estimates": {"previous": before, "current": after}}},
                  "evidence_refs": refs, "reason": "test", "created_by": "test"},
            input_refs=refs, source_refs=refs, epistemic_status="inferred",
            confidence=0.8,
        )
        return self.store.append("self.transformed", artifact)

    def test_explicit_mapping_produces_bounded_auditable_input(self):
        first = self.transform("c1", {"reasoning": 0.2}, {"reasoning": 0.4}, ["eval-1"])
        self.transform("c2", {"reasoning": 0.1}, {"reasoning": 0.4}, ["eval-2"])
        influence = self.adapter.prepare()
        self.assertEqual({"self_reasoning": 0.5}, dict(influence.neural_inputs))
        self.assertEqual(("eval-1", "eval-2"), influence.evidence_by_unit["self_reasoning"])
        self.assertIn(first.event_id, influence.transformation_event_ids)

    def test_unmapped_changes_are_ignored(self):
        self.transform("c1", {"memory": 0.1}, {"memory": 0.9}, ["eval-1"])
        self.assertEqual({}, dict(self.adapter.prepare().neural_inputs))

    def test_adapter_is_read_only(self):
        self.transform("c1", {"reasoning": 0.2}, {"reasoning": 0.4}, ["eval-1"])
        count = len(self.store.all_events())
        self.adapter.prepare()
        self.assertEqual(count, len(self.store.all_events()))
        self.store.verify_integrity()

    def test_invalid_mapping_and_gain_are_rejected(self):
        integrator = SelfExperienceIntegrator(SelfAutobiography(self.store))
        with self.assertRaises(ValueError):
            SelfInfluenceAdapter(integrator, {})
        with self.assertRaises(ValueError):
            SelfInfluenceAdapter(integrator, {"x": "unit"}, gain=3)


if __name__ == "__main__":
    unittest.main()
