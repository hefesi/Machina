import unittest

from machina.self_model import SelfModel
from machina.self_state_dynamics import SelfStateDynamicsAnalyzer


class SelfStateDynamicsAnalyzerTests(unittest.TestCase):
    def snapshot(self, cycle, value, status="observed"):
        model = SelfModel()
        refs = {"internal.metric": f"measurement:{cycle}"} if status == "observed" else {}
        model.update(
            {"internal.metric": value}, cycle_id=cycle,
            evidence_refs=refs, statuses={"internal.metric": status},
        )
        return model.snapshot()

    def test_detects_persistence_after_change(self):
        history = [self.snapshot("c1", 0.2), self.snapshot("c2", 0.7), self.snapshot("c3", 0.7)]
        result = SelfStateDynamicsAnalyzer().analyze(history, "internal.metric")
        self.assertEqual("persistent_since_change", result.status)
        self.assertEqual(3, result.observations)
        self.assertEqual(("measurement:c1", "measurement:c2", "measurement:c3"), result.evidence_refs)

    def test_detects_reversion_to_initial_value(self):
        history = [self.snapshot("c1", 0.2), self.snapshot("c2", 0.7), self.snapshot("c3", 0.2)]
        result = SelfStateDynamicsAnalyzer().analyze(history, "internal.metric")
        self.assertEqual("reverted", result.status)

    def test_detects_recurrence_without_current_reversion(self):
        history = [self.snapshot("c1", 0.2), self.snapshot("c2", 0.7), self.snapshot("c3", 0.4), self.snapshot("c4", 0.7)]
        result = SelfStateDynamicsAnalyzer().analyze(history, "internal.metric")
        self.assertEqual("recurrent", result.status)

    def test_ignores_unobserved_samples(self):
        history = [self.snapshot("c1", 0.2), self.snapshot("c2", None, "unknown"), self.snapshot("c3", 0.7)]
        result = SelfStateDynamicsAnalyzer().analyze(history, "internal.metric")
        self.assertEqual("persistent_since_change", result.status)
        self.assertEqual(2, result.observations)

    def test_requires_distinct_cycles_and_evidence(self):
        history = [self.snapshot("c1", 0.2), self.snapshot("c1", 0.7)]
        with self.assertRaises(ValueError):
            SelfStateDynamicsAnalyzer().analyze(history, "internal.metric")

    def test_analyze_all_uses_only_shared_observed_properties(self):
        history = [self.snapshot("c1", 0.2), self.snapshot("c2", 0.3)]
        result = SelfStateDynamicsAnalyzer().analyze_all(history)
        self.assertEqual(["internal.metric"], [item.property_name for item in result])


if __name__ == "__main__":
    unittest.main()
