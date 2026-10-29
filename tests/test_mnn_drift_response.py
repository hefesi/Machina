import unittest

from machina.mnn_drift_response import MNNDriftResponsePolicy


class MNNDriftResponsePolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = MNNDriftResponsePolicy()

    def test_detected_negative_and_positive_shifts_recommend_review(self):
        result = self.policy.evaluate({
            "status": "detected",
            "reason": "reward_shift_exceeds_threshold",
            "context": "quiet workload",
            "comparisons": {
                "continue": {
                    "status": "shift_detected",
                    "reward_shift": -0.8,
                    "previous_evidence_ids": ["old-1"],
                    "recent_evidence_ids": ["new-1"],
                },
                "pause": {
                    "status": "shift_detected",
                    "reward_shift": 0.7,
                    "previous_evidence_ids": ["old-2"],
                    "recent_evidence_ids": ["new-2"],
                },
                "wait": {"status": "within_threshold", "reward_shift": 0.0},
            },
        })
        self.assertEqual(result["response"], "increase_exploration_and_reassess")
        self.assertEqual(result["degraded_actions"], ["continue"])
        self.assertEqual(result["improved_actions"], ["pause"])
        self.assertEqual(result["evidence_ids"], ["new-1", "new-2", "old-1", "old-2"])
        self.assertFalse(result["changes_learner"])
        self.assertTrue(result["preserves_history"])

    def test_stable_signal_keeps_normal_monitoring(self):
        result = self.policy.evaluate({
            "status": "stable", "reason": "no_shift_exceeds_threshold",
            "context": "quiet workload",
        })
        self.assertEqual(result["response"], "continue_monitoring")
        self.assertEqual(result["shifted_actions"], [])

    def test_abstention_requests_more_evidence_not_forgetting(self):
        result = self.policy.evaluate({
            "status": "abstain", "reason": "insufficient_decision_history",
            "context": "quiet workload",
        })
        self.assertEqual(result["response"], "collect_more_evidence")
        self.assertFalse(result["changes_learner"])
        self.assertTrue(result["preserves_history"])

    def test_rejects_malformed_detected_drift(self):
        with self.assertRaises(ValueError):
            self.policy.evaluate({"status": "unknown", "reason": "x"})
        with self.assertRaises(ValueError):
            self.policy.evaluate({
                "status": "detected", "reason": "shift",
                "context": "x", "comparisons": {},
            })
        with self.assertRaises(ValueError):
            self.policy.evaluate({
                "status": "detected", "reason": "shift",
                "context": "x",
                "comparisons": {"left": {"status": "shift_detected", "reward_shift": float("nan")}},
            })


if __name__ == "__main__":
    unittest.main()
