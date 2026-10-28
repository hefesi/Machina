import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_strategy_experiment import MNNStrategyExperimentLog
from machina.mnn_strategy_evaluation import MNNStrategyExperimentEvaluator


class StrategyExperimentEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.memory = FragmentMemory(Path(self.tmp.name) / "memory.db")
        self.addCleanup(self.memory.close)
        self.log = MNNStrategyExperimentLog(self.memory, ["baseline", "candidate"])
        self.evaluator = MNNStrategyExperimentEvaluator(
            self.memory, ["baseline", "candidate"],
            min_samples_per_action=2, min_reward_margin=0.2,
        )

    def trial(self, experiment_id, action, reward, campaign="campaign-A"):
        review = {"status": "candidate", "candidate_action": "candidate"}
        self.log.begin(
            experiment_id, hypothesis="compare candidate against baseline",
            context="workload A", current_action="baseline",
            planned_action=action, review=review, campaign_id=campaign,
        )
        self.log.complete(
            experiment_id, tested_action=action, observed_reward=reward,
            decision="collect_more_data",
        )

    def test_candidate_better_after_minimum_evidence(self):
        for i, reward in enumerate((0.3, 0.4)):
            self.trial(f"base-{i}", "baseline", reward)
        for i, reward in enumerate((0.8, 0.9)):
            self.trial(f"cand-{i}", "candidate", reward)
        before = [(f.id, dict(f.metadata)) for f in self.memory.archive()]
        result = self.evaluator.evaluate("campaign-A")
        after = [(f.id, dict(f.metadata)) for f in self.memory.archive()]
        self.assertEqual("candidate_better", result["status"])
        self.assertEqual(2, result["sample_counts"]["baseline"])
        self.assertEqual(2, result["sample_counts"]["candidate"])
        self.assertFalse(result["causal_claim"])
        self.assertFalse(result["statistical_significance_claim"])
        self.assertIn("sample_standard_deviations", result)
        self.assertGreater(result["difference_standard_error"], 0)
        self.assertEqual(before, after)

    def test_current_better_and_small_margin_are_distinguished(self):
        for i, reward in enumerate((0.9, 0.8)):
            self.trial(f"base-{i}", "baseline", reward)
        for i, reward in enumerate((0.2, 0.3)):
            self.trial(f"cand-{i}", "candidate", reward)
        self.assertEqual("current_better", self.evaluator.evaluate("campaign-A")["status"])

    def test_insufficient_samples_abstains_from_conclusion(self):
        self.trial("base-1", "baseline", 0.2)
        self.trial("cand-1", "candidate", 0.9)
        result = self.evaluator.evaluate("campaign-A")
        self.assertEqual("inconclusive", result["status"])
        self.assertEqual("insufficient_samples", result["reason"])

    def test_high_reward_variability_prevents_overconfident_conclusion(self):
        for i, reward in enumerate((0.0, 1.0, 0.0, 1.0)):
            self.trial(f"noisy-base-{i}", "baseline", reward, campaign="noisy")
        for i, reward in enumerate((0.0, 2.0, 0.0, 2.0)):
            self.trial(f"noisy-cand-{i}", "candidate", reward, campaign="noisy")
        result = self.evaluator.evaluate("noisy")
        self.assertEqual("inconclusive", result["status"])
        self.assertEqual("reward_difference_not_larger_than_noise_guard", result["reason"])
        self.assertGreater(result["sample_variances"]["candidate"], result["sample_variances"]["baseline"])
        self.assertGreater(result["noise_threshold"], result["reward_difference"])

    def test_campaigns_are_isolated_and_missing_campaign_abstains(self):
        self.trial("base-1", "baseline", 0.1, campaign="other")
        self.assertEqual("abstain", self.evaluator.evaluate("campaign-A")["status"])
        self.assertEqual("abstain", self.evaluator.evaluate("missing")["status"])

    def test_mixed_context_campaign_is_rejected(self):
        self.trial("base-1", "baseline", 0.1, campaign="mixed")
        review = {"status": "candidate", "candidate_action": "candidate"}
        self.log.begin(
            "cand-1", hypothesis="different context", context="workload B",
            current_action="baseline", planned_action="candidate",
            review=review, campaign_id="mixed",
        )
        self.log.complete(
            "cand-1", tested_action="candidate", observed_reward=0.9,
            decision="collect_more_data",
        )
        result = self.evaluator.evaluate("mixed")
        self.assertEqual("abstain", result["status"])
        self.assertEqual("inconsistent_campaign_context", result["reason"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            MNNStrategyExperimentEvaluator(self.memory, ["a", "b"], min_samples_per_action=0)
        with self.assertRaises(ValueError):
            MNNStrategyExperimentEvaluator(self.memory, ["a", "b"], min_reward_margin=float("nan"))
        with self.assertRaises(ValueError):
            MNNStrategyExperimentEvaluator(self.memory, ["a", "b"], noise_guard_multiplier=-1)
        with self.assertRaises(ValueError):
            MNNStrategyExperimentEvaluator(self.memory, ["a", "b"], noise_guard_multiplier=float("inf"))
        with self.assertRaises(ValueError):
            self.evaluator.evaluate(" ")


if __name__ == "__main__":
    unittest.main()
