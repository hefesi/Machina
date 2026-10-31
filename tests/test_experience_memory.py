import tempfile
import unittest
from pathlib import Path

from machina.experience_memory import ExperienceMemoryStore


class ExperienceMemoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "experience.sqlite3"
        self.store = ExperienceMemoryStore(self.path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _begin(self, token, strategy="careful", expected=.7):
        return self.store.begin(
            token, cycle_id="cycle-1", goal_id="goal-1", strategy=strategy,
            intention="Complete the bounded task", expected_outcome=expected,
            context_ref="context:1", prediction_ref="prediction:1",
        )

    def test_intention_is_persisted_before_outcome_and_survives_restart(self):
        self._begin("exp-1")
        self.store.close()
        self.store = ExperienceMemoryStore(self.path)
        item = self.store.get("exp-1")
        self.assertFalse(item["evaluated"])
        self.assertEqual("careful", item["strategy"])
        self.assertEqual(.7, item["expected_outcome"])

    def test_outcome_compares_expectation_with_evaluator_evidence(self):
        self._begin("exp-1")
        result = self.store.record_outcome(
            "exp-1", outcome_id="out-1", observed_outcome=.4,
            evidence_ref="benchmark:1", evaluator="test-evaluator",
            note="Four of ten checks passed.",
        )
        self.assertAlmostEqual(-.3, result["prediction_error"])
        self.assertEqual("benchmark:1", result["evidence_ref"])
        self.assertTrue(self.store.get("exp-1")["evaluated"])

    def test_outcome_requires_existing_intent_and_explicit_evidence(self):
        with self.assertRaisesRegex(ValueError, "before its outcome"):
            self.store.record_outcome(
                "missing", outcome_id="out-1", observed_outcome=.5,
                evidence_ref="e:1", evaluator="human", note="Reviewed",
            )
        self._begin("exp-1")
        with self.assertRaisesRegex(ValueError, "evidence_ref"):
            self.store.record_outcome(
                "exp-1", outcome_id="out-1", observed_outcome=.5,
                evidence_ref=" ", evaluator="human", note="Reviewed",
            )

    def test_intent_and_outcome_ids_are_idempotent_but_conflicts_rejected(self):
        self._begin("exp-1")
        self.assertTrue(self._begin("exp-1")["already_recorded"])
        with self.assertRaisesRegex(ValueError, "different intent"):
            self.store.begin(
                "exp-1", cycle_id="cycle-2", goal_id="goal-1",
                strategy="careful", intention="Changed", expected_outcome=.7,
            )
        args = dict(outcome_id="out-1", observed_outcome=.8,
                    evidence_ref="e:1", evaluator="human", note="Verified")
        self.store.record_outcome("exp-1", **args)
        self.assertTrue(self.store.record_outcome("exp-1", **args)["already_recorded"])
        with self.assertRaisesRegex(ValueError, "different outcome"):
            self.store.record_outcome("exp-1", **{**args, "observed_outcome": .2})

    def test_outcome_ids_cannot_be_reused_for_another_experience(self):
        self._begin("exp-1")
        self._begin("exp-2")
        args = dict(outcome_id="same", observed_outcome=.8,
                    evidence_ref="e:1", evaluator="human", note="Verified")
        self.store.record_outcome("exp-1", **args)
        with self.assertRaisesRegex(ValueError, "already been used"):
            self.store.record_outcome("exp-2", **args)

    def test_strategy_patterns_require_minimum_sample_and_are_non_causal(self):
        for index, score in enumerate((.8, .9, .7), 1):
            self._begin(f"a-{index}", "strategy-a", .7)
            self.store.record_outcome(
                f"a-{index}", outcome_id=f"oa-{index}", observed_outcome=score,
                evidence_ref=f"ea-{index}", evaluator="reviewer", note="Evaluated",
            )
        for index, score in enumerate((.2, .3, .4), 1):
            self._begin(f"b-{index}", "strategy-b", .7)
            self.store.record_outcome(
                f"b-{index}", outcome_id=f"ob-{index}", observed_outcome=score,
                evidence_ref=f"eb-{index}", evaluator="reviewer", note="Evaluated",
            )
        report = self.store.strategy_report(minimum_samples=3, minimum_difference=.2)
        self.assertTrue(report["comparisons"][0]["descriptive_signal"])
        self.assertEqual("observational_comparison_not_causal",
                         report["comparisons"][0]["interpretation"])
        self.assertTrue(report["recommendation_only"])
        self.assertFalse(report["policy_changed"])
        self.assertFalse(report["execution_performed"])

    def test_invalid_scores_and_thresholds_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "expected_outcome"):
            self.store.begin(
                "bad", cycle_id="c", goal_id="g", strategy="s",
                intention="Do work", expected_outcome=float("nan"),
            )
        with self.assertRaisesRegex(ValueError, "observed_outcome"):
            self._begin("exp-1")
            self.store.record_outcome(
                "exp-1", outcome_id="o", observed_outcome=2,
                evidence_ref="e", evaluator="human", note="bad",
            )
        with self.assertRaisesRegex(ValueError, "minimum_samples"):
            self.store.strategy_report(minimum_samples=1)


if __name__ == "__main__":
    unittest.main()
