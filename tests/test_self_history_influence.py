import unittest

from machina.self_state_dynamics import SelfStateTransition
from machina.self_history_influence import SelfHistoryInfluenceAdapter, SelfHistoryRule


class SelfHistoryInfluenceTests(unittest.TestCase):
    def setUp(self):
        self.adapter = SelfHistoryInfluenceAdapter([
            SelfHistoryRule("internal.metric", {
                "persistent_since_change": {"maintain_progress": 0.12},
                "reverted": {"review_strategy": -0.08},
                "recurrent": {"investigate_pattern": 0.1},
            })
        ])

    def transition(self, status, prop="internal.metric"):
        return SelfStateTransition(prop, 0.1, 0.8, "c1", "c3", 3, status,
                                   ("evidence:c1", "evidence:c3"))

    def test_persistent_history_produces_configured_bounded_adjustment(self):
        result = self.adapter.prepare([self.transition("persistent_since_change")])
        self.assertEqual({"maintain_progress": 0.12}, result.adjustments)
        self.assertEqual(("evidence:c1", "evidence:c3"), result.evidence_refs)

    def test_reversion_and_recurrence_have_distinct_policies(self):
        result = self.adapter.prepare([self.transition("reverted"), self.transition("recurrent")])
        self.assertEqual({"review_strategy": -0.08, "investigate_pattern": 0.1}, result.adjustments)

    def test_unmapped_history_does_not_influence_decisions(self):
        result = self.adapter.prepare([self.transition("changed", "unmapped")])
        self.assertEqual({}, result.adjustments)
        self.assertEqual((), result.transitions)

    def test_combined_adjustments_are_clamped(self):
        adapter = SelfHistoryInfluenceAdapter([
            SelfHistoryRule("a", {"stable": {"drive": 0.2}}),
            SelfHistoryRule("b", {"stable": {"drive": 0.2}}),
        ])
        transitions = [
            SelfStateTransition(name, 1, 1, "c1", "c2", 2, "stable", (f"ev:{name}",))
            for name in ("a", "b")
        ]
        self.assertEqual({"drive": 0.3}, adapter.prepare(transitions).adjustments)

    def test_rejects_invalid_adjustments(self):
        with self.assertRaises(ValueError):
            SelfHistoryInfluenceAdapter([
                SelfHistoryRule("a", {"stable": {"drive": 0.4}})
            ])


if __name__ == "__main__":
    unittest.main()
