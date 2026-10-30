import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_strategy_experiment import MNNStrategyExperimentLog
from machina.mnn_strategy_evaluation import MNNStrategyExperimentEvaluator
from machina.mnn_strategy_context_memory import MNNStrategyContextMemory


class StrategyContextMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.memory = FragmentMemory(Path(self.tmp.name) / "memory.db")
        self.addCleanup(self.memory.close)
        self.log = MNNStrategyExperimentLog(self.memory, ["baseline", "candidate"])
        self.evaluator = MNNStrategyExperimentEvaluator(
            self.memory, ["baseline", "candidate"], min_samples_per_action=2,
            min_reward_margin=0.2,
        )
        self.context_memory = MNNStrategyContextMemory(self.evaluator)

    def campaign(self, campaign_id, context, baseline, candidate):
        review = {"status": "candidate", "candidate_action": "candidate"}
        for action, rewards in (("baseline", baseline), ("candidate", candidate)):
            for index, reward in enumerate(rewards):
                experiment_id = f"{campaign_id}-{action}-{index}"
                self.log.begin(
                    experiment_id, hypothesis="compare strategies", context=context,
                    current_action="baseline", planned_action=action, review=review,
                    campaign_id=campaign_id,
                )
                self.log.complete(
                    experiment_id, tested_action=action, observed_reward=reward,
                    decision="collect_more_data",
                )

    def test_contexts_keep_opposite_strategy_results_separate(self):
        for campaign in ("a1", "a2", "a3"):
            self.campaign(campaign, "workload A", (0.1, 0.2), (0.8, 0.9))
        for campaign in ("b1", "b2", "b3"):
            self.campaign(campaign, "workload B", (0.8, 0.9), (0.1, 0.2))
        before = [(item.id, dict(item.metadata)) for item in self.memory.archive()]
        result = self.context_memory.review({
            "workload A": ["a1", "a2", "a3"],
            "workload B": ["b1", "b2", "b3"],
        })
        after = [(item.id, dict(item.metadata)) for item in self.memory.archive()]
        profiles = result["profiles"]
        self.assertEqual("consistent_candidate_advantage",
                         profiles["workload a"]["aggregate"]["status"])
        self.assertEqual("consistent_current_advantage",
                         profiles["workload b"]["aggregate"]["status"])
        self.assertTrue(result["contexts_kept_separate"])
        self.assertFalse(result["raw_trials_pooled"])
        self.assertFalse(result["policy_changed"])
        self.assertEqual(before, after)

    def test_requested_context_must_match_stored_context(self):
        for campaign in ("a1", "a2", "a3"):
            self.campaign(campaign, "actual workload", (0.1, 0.2), (0.8, 0.9))
        result = self.context_memory.review({"different workload": ["a1", "a2", "a3"]})
        profile = result["profiles"]["different workload"]
        self.assertEqual("abstain", profile["aggregate"]["status"])
        self.assertEqual("requested_context_does_not_match_stored_context",
                         profile["aggregate"]["reason"])

    def test_campaign_cannot_be_assigned_to_two_contexts(self):
        with self.assertRaises(ValueError):
            self.context_memory.review({"A": ["same"], "B": ["same"]})

    def test_insufficient_campaign_evidence_remains_inconclusive(self):
        self.campaign("only-one", "workload A", (0.1, 0.2), (0.8, 0.9))
        result = self.context_memory.review({"workload A": ["only-one"]})
        self.assertEqual("inconclusive",
                         result["profiles"]["workload a"]["aggregate"]["status"])


if __name__ == "__main__":
    unittest.main()
