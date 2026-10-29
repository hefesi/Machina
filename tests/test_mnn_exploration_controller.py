import json
import unittest
from machina.mnn_exploration_controller import MNNBoundedExplorationController

def review(response="increase_exploration_and_reassess", evidence=None):
    return {"recommendation": {"response": response, "context": "busy workload",
            "evidence_ids": evidence if evidence is not None else ["old-1", "new-1"]}}

class MNNBoundedExplorationControllerTests(unittest.TestCase):
    def test_new_drift_evidence_activates_bounded_exploration(self):
        controller = MNNBoundedExplorationController(base_epsilon=0.05, elevated_epsilon=0.3, duration_decisions=3)
        result = controller.observe_review(review(), decision_index=10)
        self.assertEqual(result["status"], "activated")
        self.assertEqual(result["active_until_decision"], 12)
        self.assertEqual(controller.epsilon_for(10), 0.3)
        self.assertEqual(controller.epsilon_for(12), 0.3)
        self.assertEqual(controller.epsilon_for(13), 0.05)

    def test_same_evidence_cannot_extend_exploration_window(self):
        controller = MNNBoundedExplorationController(duration_decisions=3)
        controller.observe_review(review(), decision_index=10)
        duplicate = controller.observe_review(review(), decision_index=12)
        self.assertEqual(duplicate["status"], "duplicate_evidence")
        self.assertEqual(controller.active_until_decision, 12)
        self.assertEqual(controller.epsilon_for(13), controller.base_epsilon)

    def test_distinct_evidence_can_reactivate_window(self):
        controller = MNNBoundedExplorationController(duration_decisions=2)
        controller.observe_review(review(), decision_index=1)
        result = controller.observe_review(review(evidence=["old-2", "new-2"]), decision_index=8)
        self.assertEqual(result["status"], "activated")
        self.assertEqual(controller.active_until_decision, 9)

    def test_stable_or_abstaining_review_does_not_change_schedule(self):
        controller = MNNBoundedExplorationController()
        result = controller.observe_review(review("collect_more_evidence"), decision_index=4)
        self.assertEqual(result["status"], "no_change")
        self.assertIsNone(controller.active_until_decision)

    def test_snapshot_restores_expiry_and_duplicate_guard(self):
        controller = MNNBoundedExplorationController(duration_decisions=4)
        controller.observe_review(review(), decision_index=5)
        restored = MNNBoundedExplorationController.from_snapshot(json.loads(json.dumps(controller.snapshot())))
        self.assertEqual(restored.epsilon_for(8), controller.elevated_epsilon)
        self.assertEqual(restored.epsilon_for(9), controller.base_epsilon)
        self.assertEqual(restored.observe_review(review(), decision_index=9)["status"], "duplicate_evidence")

    def test_rejects_invalid_configuration_and_missing_evidence(self):
        with self.assertRaises(ValueError):
            MNNBoundedExplorationController(base_epsilon=0.4, elevated_epsilon=0.2)
        with self.assertRaises(ValueError):
            MNNBoundedExplorationController(duration_decisions=0)
        with self.assertRaises(ValueError):
            MNNBoundedExplorationController().observe_review(review(evidence=[]), decision_index=0)

if __name__ == "__main__":
    unittest.main()
