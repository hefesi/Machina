import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_strategy_experiment import MNNStrategyExperimentLog
from machina.mnn_strategy_evaluation import MNNStrategyExperimentEvaluator
from machina.mnn_strategy_context_memory import MNNStrategyContextMemory
from machina.mnn_strategy_decision_advisor import MNNStrategyDecisionAdvisor


class StrategyDecisionAdvisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.memory = FragmentMemory(Path(self.tmp.name) / "memory.db")
        self.addCleanup(self.memory.close)
        self.log = MNNStrategyExperimentLog(self.memory, ["baseline", "candidate"])
        evaluator = MNNStrategyExperimentEvaluator(
            self.memory, ["baseline", "candidate"],
            min_samples_per_action=2, min_reward_margin=0.2,
        )
        self.advisor = MNNStrategyDecisionAdvisor(MNNStrategyContextMemory(evaluator))

    def campaign(self, campaign_id, baseline, candidate):
        review = {"status": "candidate", "candidate_action": "candidate"}
        for action, rewards in (("baseline", baseline), ("candidate", candidate)):
            for index, reward in enumerate(rewards):
                experiment_id = f"{campaign_id}-{action}-{index}"
                self.log.begin(
                    experiment_id, hypothesis="compare actions", context="workload A",
                    current_action="baseline", planned_action=action,
                    review=review, campaign_id=campaign_id,
                )
                self.log.complete(
                    experiment_id, tested_action=action, observed_reward=reward,
                    decision="collect_more_data",
                )

    def test_proposes_repeated_candidate_advantage_with_evidence(self):
        for campaign in ("c1", "c2", "c3"):
            self.campaign(campaign, (0.1, 0.2), (0.8, 0.9))
        before = [(item.id, dict(item.metadata)) for item in self.memory.archive()]
        result = self.advisor.propose("workload A", ["c1", "c2", "c3"])
        after = [(item.id, dict(item.metadata)) for item in self.memory.archive()]
        self.assertEqual("proposed", result["status"])
        self.assertEqual("candidate", result["action"])
        self.assertTrue(result["evidence_ids"])
        self.assertFalse(result["executed"])
        self.assertFalse(result["policy_changed"])
        self.assertTrue(result["requires_external_execution"])
        self.assertEqual(before, after)

    def test_abstains_when_campaigns_disagree(self):
        self.campaign("c1", (0.1, 0.2), (0.8, 0.9))
        self.campaign("c2", (0.1, 0.2), (0.8, 0.9))
        self.campaign("c3", (0.8, 0.9), (0.1, 0.2))
        result = self.advisor.propose("workload A", ["c1", "c2", "c3"])
        self.assertEqual("abstain", result["status"])
        self.assertIsNone(result["action"])
        self.assertFalse(result["executed"])

    def test_abstains_when_context_does_not_match(self):
        for campaign in ("c1", "c2", "c3"):
            self.campaign(campaign, (0.1, 0.2), (0.8, 0.9))
        result = self.advisor.propose("different context", ["c1", "c2", "c3"])
        self.assertEqual("abstain", result["status"])
        self.assertIsNone(result["action"])

    def test_validates_campaign_ids(self):
        with self.assertRaises(ValueError):
            self.advisor.propose("workload A", "c1")
        with self.assertRaises(ValueError):
            self.advisor.propose("workload A", ["c1", "c1"])


if __name__ == "__main__":
    unittest.main()
