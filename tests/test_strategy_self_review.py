import tempfile
import unittest
from pathlib import Path

from machina.experience_memory import ExperienceMemoryStore
from machina.strategy_self_review import StrategySelfReviewStore


class StrategySelfReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.experiences = ExperienceMemoryStore(root / "experiences.db")
        self.reviews = StrategySelfReviewStore(root / "reviews.db")

    def tearDown(self):
        self.reviews.close()
        self.experiences.close()
        self.tmp.cleanup()

    def _report(self, count=3):
        for index in range(count):
            experience_id = f"experience-{index}"
            self.experiences.begin(
                experience_id, cycle_id=f"cycle-{index}", goal_id="goal",
                strategy="baseline", intention="Attempt task",
                expected_outcome=.8,
            )
            self.experiences.record_outcome(
                experience_id, outcome_id=f"outcome-{index}",
                observed_outcome=.2 + index * .05,
                evidence_ref=f"benchmark:{index}", evaluator="reviewer",
                note="Evaluator-scored result",
            )
        return self.experiences.autobiographical_report(
            minimum_repetitions=2, error_threshold=.1
        )

    def _propose(self, report, proposal_id="review-1"):
        return self.reviews.propose(
            proposal_id, autobiographical_report=report, goal_id="goal",
            strategy="baseline", alternative_strategy="conservative-v2",
            hypothesis="Reducing the task scope may improve measured completion.",
            rationale="The repeated underestimation pattern warrants a testable alternative.",
            outcome_metric="evaluator completion score",
            confounders=["task difficulty may differ", "evaluator scoring may drift"],
            minimum_repetitions=3,
        )

    def test_repeated_pattern_creates_explicit_hypothesis_proposal(self):
        result = self._propose(self._report())
        self.assertEqual("proposed", result["status"])
        self.assertEqual(["benchmark:0", "benchmark:1", "benchmark:2"],
                         result["proposal"]["evidence_refs"])
        self.assertFalse(result["experiment_started"])
        self.assertFalse(result["policy_changed"])
        self.assertFalse(result["execution_performed"])

    def test_insufficient_history_cannot_create_proposal(self):
        with self.assertRaisesRegex(ValueError, "minimum_repetitions"):
            self._propose(self._report(count=2))

    def test_hypothesis_and_confounders_are_required(self):
        report = self._report()
        with self.assertRaisesRegex(ValueError, "hypothesis"):
            self.reviews.propose(
                "bad", autobiographical_report=report, goal_id="goal",
                strategy="baseline", alternative_strategy="new",
                hypothesis=" ", rationale="Reason", outcome_metric="score",
                confounders=["unknown difficulty"],
            )
        with self.assertRaisesRegex(ValueError, "confounders"):
            self.reviews.propose(
                "bad", autobiographical_report=report, goal_id="goal",
                strategy="baseline", alternative_strategy="new",
                hypothesis="Testable hypothesis", rationale="Reason",
                outcome_metric="score", confounders=[],
            )

    def test_evidence_must_be_grounded_in_matching_report_pattern(self):
        report = self._report()
        report["patterns"][0]["evidence_refs"] = ["invented:evidence"]
        with self.assertRaisesRegex(ValueError, "pattern evidence_refs"):
            self._propose(report)

    def test_proposal_is_idempotent_and_conflicts_are_rejected(self):
        report = self._report()
        first = self._propose(report)
        retry = self._propose(report)
        self.assertTrue(retry["already_recorded"])
        self.assertEqual(first["proposal"], retry["proposal"])
        with self.assertRaisesRegex(ValueError, "different content"):
            self.reviews.propose(
                "review-1", autobiographical_report=report, goal_id="goal",
                strategy="baseline", alternative_strategy="new",
                hypothesis="Different hypothesis", rationale="Reason",
                outcome_metric="score", confounders=["different context"],
            )

    def test_explicit_decision_is_append_only_and_approval_does_not_apply(self):
        self._propose(self._report())
        result = self.reviews.decide(
            "review-1", decision_id="decision-1", decision="approved",
            rationale="Approved for a separately controlled evaluation.",
            authorization_ref="human-approval:42",
        )
        self.assertEqual("approved", result["status"])
        self.assertFalse(result["experiment_started"])
        self.assertFalse(result["policy_changed"])
        self.assertFalse(result["execution_performed"])
        with self.assertRaisesRegex(ValueError, "final decision"):
            self.reviews.decide(
                "review-1", decision_id="decision-2", decision="rejected",
                rationale="Changed mind", authorization_ref="human-approval:43",
            )

    def test_decision_ids_are_idempotent_and_conflicts_rejected(self):
        self._propose(self._report())
        args = dict(decision_id="decision-1", decision="rejected",
                    rationale="Not worth testing", authorization_ref="human:1")
        self.reviews.decide("review-1", **args)
        retry = self.reviews.decide("review-1", **args)
        self.assertTrue(retry["already_recorded"])
        with self.assertRaisesRegex(ValueError, "different content"):
            self.reviews.decide(
                "review-1", **{**args, "rationale": "Changed rationale"}
            )

    def test_history_survives_restart(self):
        self._propose(self._report())
        self.reviews.close()
        self.reviews = StrategySelfReviewStore(
            Path(self.tmp.name) / "reviews.db"
        )
        self.assertEqual("proposed", self.reviews.history()[0]["status"])


if __name__ == "__main__":
    unittest.main()
