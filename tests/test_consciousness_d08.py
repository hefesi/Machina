from __future__ import annotations

import unittest

from machina.relevance import EventSignals, RelevanceWeights, score_relevance
from machina.self_continuity import SelfContinuity
from machina.subjective_state import FunctionalSubjectiveState


class FunctionalSubjectivityTests(unittest.TestCase):
    def test_state_tracks_world_self_unknowns_and_provenance(self):
        state = FunctionalSubjectiveState()
        state.set_world_fact("weather", "rain", "sensor:weather", 0.9)
        state.set_self_fact("can_write_file", True, "capability_test", 1.0)
        state.mark_unknown("battery")
        state.mark_unknown("current_goal", about_self=True)
        snapshot = state.snapshot()
        self.assertEqual("sensor:weather", snapshot["world"]["weather"]["source"])
        self.assertEqual("capability_test", snapshot["self_model"]["can_write_file"]["source"])
        self.assertIn("battery", snapshot["unknowns"])
        self.assertIn("self:current_goal", snapshot["unknowns"])

    def test_memory_importance_and_validation(self):
        state = FunctionalSubjectiveState()
        state.add_memory("completed task", source="execution_log", importance=0.8)
        self.assertEqual(0.8, state.snapshot()["memories"][0]["importance"])
        with self.assertRaises(ValueError):
            state.add_memory("bad", source="test", importance=1.2)

    def test_self_continuity_detects_identity_and_change_history(self):
        before = SelfContinuity("machina-1", commitments={"learn": "active"}, component_versions={"mnn": "0.3"})
        before.record_event("boot", "runtime")
        after = SelfContinuity(
            "machina-1",
            commitments={"learn": "paused"},
            event_history=list(before.event_history),
            component_versions={"mnn": "0.4"},
        )
        after.record_event("commitment changed", "policy", reason="new evidence")
        report = after.continuity_report(before)
        self.assertTrue(report["same_agent_id"])
        self.assertTrue(report["history_extends_previous"])
        self.assertFalse(report["commitments_preserved"]["learn"])
        self.assertTrue(report["component_versions"]["mnn"]["changed"])

    def test_relevance_changes_with_operational_signals(self):
        low = EventSignals(0.1, 0.1, 0.1, 0.1)
        high = EventSignals(0.9, 0.9, 0.9, 0.9)
        self.assertLess(score_relevance(low), score_relevance(high))
        self.assertAlmostEqual(0.5, score_relevance(EventSignals(0.5, 0.5, 0.5, 0.5)))

    def test_weights_are_normalized(self):
        signals = EventSignals(1.0, 0.0, 0.0, 0.0)
        weights = RelevanceWeights(goal_alignment=2.0, novelty=0.0, future_decision_impact=0.0, urgency=0.0)
        with self.assertRaises(ValueError):
            score_relevance(signals, weights)

    def test_functional_dimensions_do_not_claim_phenomenal_consciousness(self):
        from pathlib import Path
        document = Path("docs/CONSCIOUSNESS_D08_FORMAL_MODEL.md").read_text()
        self.assertIn("não implica qualia", document)
        self.assertIn("experiência fenomenal", document)


if __name__ == "__main__":
    unittest.main()
