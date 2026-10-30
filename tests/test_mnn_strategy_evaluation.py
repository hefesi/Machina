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

    def test_temporal_review_detects_reversed_advantage(self):
        sequence = [
            ("baseline", 0.3), ("candidate", 0.8),
            ("baseline", 0.3), ("candidate", 0.9),
            ("baseline", 0.4), ("candidate", 0.1),
            ("baseline", 0.3), ("candidate", 0.0),
        ]
        for i, (action, reward) in enumerate(sequence):
            self.trial(f"temporal-{i}", action, reward, campaign="temporal")
        result = self.evaluator.evaluate_over_time("temporal", window_size=2)
        self.assertEqual("advantage_reversed", result["status"])
        self.assertGreater(result["early_advantage"], 0)
        self.assertLess(result["late_advantage"], 0)
        self.assertFalse(result["causal_claim"])
        self.assertFalse(result["statistical_significance_claim"])
        self.assertEqual(2, len(result["action_windows"]["baseline"]["early_evidence_ids"]))
        self.assertEqual(2, len(result["action_windows"]["candidate"]["late_evidence_ids"]))

    def test_temporal_review_reports_persistent_advantage(self):
        sequence = [
            ("baseline", 0.2), ("candidate", 0.7),
            ("baseline", 0.3), ("candidate", 0.8),
            ("baseline", 0.2), ("candidate", 0.7),
            ("baseline", 0.3), ("candidate", 0.9),
        ]
        for i, (action, reward) in enumerate(sequence):
            self.trial(f"persistent-{i}", action, reward, campaign="persistent")
        result = self.evaluator.evaluate_over_time("persistent", window_size=2)
        self.assertEqual("advantage_persisted", result["status"])
        self.assertGreaterEqual(result["early_advantage"], self.evaluator.min_reward_margin)
        self.assertGreaterEqual(result["late_advantage"], self.evaluator.min_reward_margin)

    def test_temporal_review_requires_two_disjoint_windows(self):
        self.trial("temporal-base", "baseline", 0.2, campaign="too-short")
        self.trial("temporal-candidate", "candidate", 0.8, campaign="too-short")
        result = self.evaluator.evaluate_over_time("too-short", window_size=2)
        self.assertEqual("inconclusive", result["status"])
        self.assertEqual("insufficient_temporal_samples", result["reason"])


    def test_temporal_review_abstains_when_advantage_is_smaller_than_variability(self):
        sequence = [
            ("baseline", 0.0), ("candidate", 1.3),
            ("baseline", 2.0), ("candidate", 3.3),
            ("baseline", 0.0), ("candidate", 1.3),
            ("baseline", 2.0), ("candidate", 3.3),
        ]
        for i, (action, reward) in enumerate(sequence):
            self.trial(f"noisy-temporal-{i}", action, reward, campaign="noisy-temporal")
        result = self.evaluator.evaluate_over_time("noisy-temporal", window_size=2)
        self.assertEqual("no_clear_change", result["status"])
        self.assertGreater(result["early_difference_standard_error"], result["early_advantage"])
        self.assertGreater(result["late_difference_standard_error"], result["late_advantage"])
        self.assertIn("early_noise_threshold", result)
        self.assertFalse(result["causal_claim"])

    def test_temporal_window_size_validation(self):
        with self.assertRaises(ValueError):
            self.evaluator.evaluate_over_time("campaign-A", window_size=1)

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


    def test_cross_campaign_review_requires_repeated_agreement(self):
        for campaign in ("replicate-1", "replicate-2", "replicate-3"):
            for i, reward in enumerate((0.2, 0.3)):
                self.trial(f"{campaign}-base-{i}", "baseline", reward, campaign=campaign)
            for i, reward in enumerate((0.8, 0.9)):
                self.trial(f"{campaign}-candidate-{i}", "candidate", reward, campaign=campaign)
        before = [(f.id, dict(f.metadata)) for f in self.memory.archive()]
        result = self.evaluator.evaluate_across_campaigns(
            ["replicate-1", "replicate-2", "replicate-3"]
        )
        after = [(f.id, dict(f.metadata)) for f in self.memory.archive()]
        self.assertEqual("consistent_candidate_advantage", result["status"])
        self.assertEqual(3, result["conclusive_campaign_count"])
        self.assertEqual(1.0, result["agreement_fraction"])
        self.assertFalse(result["causal_claim"])
        self.assertFalse(result["statistical_significance_claim"])
        self.assertFalse(result["raw_trials_pooled"])
        self.assertEqual(before, after)

    def test_cross_campaign_review_reports_mixed_outcomes(self):
        for campaign, baseline, candidate in (
            ("replicate-A", (0.2, 0.3), (0.8, 0.9)),
            ("replicate-B", (0.2, 0.3), (0.8, 0.9)),
            ("replicate-C", (0.8, 0.9), (0.2, 0.3)),
        ):
            for i, reward in enumerate(baseline):
                self.trial(f"{campaign}-base-{i}", "baseline", reward, campaign=campaign)
            for i, reward in enumerate(candidate):
                self.trial(f"{campaign}-candidate-{i}", "candidate", reward, campaign=campaign)
        result = self.evaluator.evaluate_across_campaigns(
            ["replicate-A", "replicate-B", "replicate-C"]
        )
        self.assertEqual("mixed_results", result["status"])
        self.assertAlmostEqual(2 / 3, result["agreement_fraction"])

    def test_cross_campaign_review_rejects_different_contexts(self):
        for campaign in ("context-A", "context-B"):
            self.trial(f"{campaign}-base", "baseline", 0.2, campaign=campaign)
            self.trial(f"{campaign}-candidate", "candidate", 0.9, campaign=campaign)
        review = {"status": "candidate", "candidate_action": "candidate"}
        self.log.begin(
            "context-B-extra", hypothesis="different context", context="workload B",
            current_action="baseline", planned_action="candidate", review=review,
            campaign_id="context-B",
        )
        result = self.evaluator.evaluate_across_campaigns(["context-A", "context-B"])
        self.assertEqual("abstain", result["status"])
        self.assertEqual("inconsistent_campaign_context", result["reason"])

    def test_cross_campaign_validation(self):
        with self.assertRaises(ValueError):
            self.evaluator.evaluate_across_campaigns("campaign-A")
        with self.assertRaises(ValueError):
            self.evaluator.evaluate_across_campaigns(["campaign-A", "campaign-A"])
        with self.assertRaises(ValueError):
            self.evaluator.evaluate_across_campaigns(
                ["campaign-A"], min_conclusive_campaigns=1
            )
        with self.assertRaises(ValueError):
            self.evaluator.evaluate_across_campaigns(
                ["campaign-A"], min_agreement_fraction=0.5
            )

    def test_holdout_validation_requires_independent_replication(self):
        exploration = ("explore-1", "explore-2", "explore-3")
        validation = ("holdout-1", "holdout-2", "holdout-3")
        for campaign in exploration + validation:
            for i, reward in enumerate((0.2, 0.3)):
                self.trial(f"{campaign}-base-{i}", "baseline", reward, campaign=campaign)
            for i, reward in enumerate((0.8, 0.9)):
                self.trial(f"{campaign}-candidate-{i}", "candidate", reward, campaign=campaign)
        before = [(f.id, dict(f.metadata)) for f in self.memory.archive()]
        result = self.evaluator.evaluate_with_holdout(exploration, validation)
        after = [(f.id, dict(f.metadata)) for f in self.memory.archive()]
        self.assertEqual("candidate_replicated", result["status"])
        self.assertTrue(result["groups_disjoint"])
        self.assertFalse(result["raw_trials_pooled"])
        self.assertFalse(result["causal_claim"])
        self.assertEqual(before, after)

    def test_holdout_validation_detects_failure_to_replicate(self):
        for campaign in ("explore-1", "explore-2"):
            for i, reward in enumerate((0.2, 0.3)):
                self.trial(f"{campaign}-base-{i}", "baseline", reward, campaign=campaign)
            for i, reward in enumerate((0.8, 0.9)):
                self.trial(f"{campaign}-candidate-{i}", "candidate", reward, campaign=campaign)
        for campaign in ("holdout-1", "holdout-2"):
            for i, reward in enumerate((0.8, 0.9)):
                self.trial(f"{campaign}-base-{i}", "baseline", reward, campaign=campaign)
            for i, reward in enumerate((0.2, 0.3)):
                self.trial(f"{campaign}-candidate-{i}", "candidate", reward, campaign=campaign)
        result = self.evaluator.evaluate_with_holdout(
            ["explore-1", "explore-2"], ["holdout-1", "holdout-2"]
        )
        self.assertEqual("not_replicated", result["status"])

    def test_holdout_validation_rejects_overlapping_campaigns(self):
        with self.assertRaises(ValueError):
            self.evaluator.evaluate_with_holdout(["same"], ["same"])

    def test_holdout_validation_requires_unique_campaign_ids(self):
        with self.assertRaises(ValueError):
            self.evaluator.evaluate_with_holdout(["a", "a"], ["b", "c"])

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
