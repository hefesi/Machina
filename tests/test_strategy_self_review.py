import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from machina.experience_memory import ExperienceMemoryStore
from machina.causal_learning import CausalExperimentStore
from machina.strategy_self_review import StrategySelfReviewStore


class StrategySelfReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.experiences = ExperienceMemoryStore(root / "experiences.db")
        self.reviews = StrategySelfReviewStore(root / "reviews.db")
        self.causal = CausalExperimentStore(root / "causal.db")

    def tearDown(self):
        self.causal.close()
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

    def test_concurrent_identical_proposals_are_idempotent(self):
        report = self._report()
        database = Path(self.tmp.name) / "reviews.db"
        barrier = threading.Barrier(2)

        def propose(_):
            store = StrategySelfReviewStore(database)
            try:
                barrier.wait(timeout=5)
                return store.propose(
                    "review-concurrent", autobiographical_report=report,
                    goal_id="goal", strategy="baseline",
                    alternative_strategy="conservative-v2",
                    hypothesis="Reducing the task scope may improve measured completion.",
                    rationale="The repeated underestimation pattern warrants a testable alternative.",
                    outcome_metric="evaluator completion score",
                    confounders=["task difficulty may differ", "evaluator scoring may drift"],
                    minimum_repetitions=3,
                )
            finally:
                store.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(propose, range(2)))

        self.assertEqual(1, sum(not item["already_recorded"] for item in results))
        self.assertEqual(1, sum(item["already_recorded"] for item in results))
        self.assertEqual(results[0]["proposal"], results[1]["proposal"])
        self.assertEqual(1, len(self.reviews.history()))

    def test_concurrent_final_decisions_are_serialized(self):
        self._propose(self._report())
        database = Path(self.tmp.name) / "reviews.db"
        barrier = threading.Barrier(2)

        def decide(decision_id, choice):
            store = StrategySelfReviewStore(database)
            try:
                barrier.wait(timeout=5)
                result = store.decide(
                    "review-1", decision_id=decision_id, decision=choice,
                    rationale=f"Concurrent {choice} decision",
                    authorization_ref=f"human:{decision_id}",
                )
                return ("recorded", result["status"])
            except ValueError as exc:
                return ("rejected", str(exc))
            finally:
                store.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(
                lambda args: decide(*args),
                (("decision-approved", "approved"), ("decision-rejected", "rejected")),
            ))

        self.assertEqual(1, sum(status == "recorded" for status, _ in results))
        self.assertEqual(1, sum(status == "rejected" for status, _ in results))
        rejection = next(detail for status, detail in results if status == "rejected")
        self.assertIn("final decision", rejection)

    def test_legacy_duplicate_final_decisions_fail_closed(self):
        database = Path(self.tmp.name) / "legacy-reviews.db"
        connection = sqlite3.connect(database)
        connection.execute("""
            CREATE TABLE strategy_review_decisions (
                decision_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL,
                decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
                rationale TEXT NOT NULL,
                authorization_ref TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.executemany(
            "INSERT INTO strategy_review_decisions "
            "(decision_id, proposal_id, decision, rationale, authorization_ref) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("legacy-approved", "legacy-proposal", "approved", "first", "human:1"),
                ("legacy-rejected", "legacy-proposal", "rejected", "second", "human:2"),
            ],
        )
        connection.commit()
        connection.close()

        with self.assertRaisesRegex(RuntimeError, "multiple final decisions"):
            StrategySelfReviewStore(database)

    def test_unapproved_strategy_review_cannot_register_causal_experiment(self):
        self._propose(self._report())
        with self.assertRaisesRegex(ValueError, "explicit approved decision"):
            self.reviews.register_approved_experiment(
                "review-1", self.causal, experiment_id="experiment-1",
                design="randomized", protocol_ref="protocol:experiment-1",
            )
        with self.assertRaisesRegex(ValueError, "unknown experiment_id"):
            self.causal.experiment("experiment-1")

    def test_approved_strategy_review_registers_causal_experiment_idempotently(self):
        self._propose(self._report())
        self.reviews.decide(
            "review-1", decision_id="decision-1", decision="approved",
            rationale="Approved for a separately controlled evaluation.",
            authorization_ref="human-approval:42",
        )
        first = self.reviews.register_approved_experiment(
            "review-1", self.causal, experiment_id="experiment-1",
            design="randomized", protocol_ref="protocol:experiment-1",
        )
        self.assertFalse(first["already_registered"])
        self.assertTrue(first["experiment_definition_created"])
        self.assertEqual("conservative-v2", first["experiment"]["treatment_name"])
        self.assertEqual("baseline", first["experiment"]["control_name"])
        self.assertEqual("human-approval:42", first["authorization_ref"])
        self.assertFalse(first["execution_performed"])
        self.assertFalse(first["policy_changed"])
        self.assertEqual(
            "insufficient_evidence",
            self.causal.report("experiment-1")["classification"],
        )

        repeated = self.reviews.register_approved_experiment(
            "review-1", self.causal, experiment_id="experiment-1",
            design="randomized", protocol_ref="protocol:experiment-1",
        )
        self.assertTrue(repeated["already_registered"])
        self.assertFalse(repeated["experiment_definition_created"])
        with self.assertRaisesRegex(ValueError, "different experiment"):
            self.reviews.register_approved_experiment(
                "review-1", self.causal, experiment_id="experiment-2",
                design="randomized", protocol_ref="protocol:experiment-2",
            )

        self.reviews.close()
        self.reviews = StrategySelfReviewStore(
            Path(self.tmp.name) / "reviews.db"
        )
        after_restart = self.reviews.register_approved_experiment(
            "review-1", self.causal, experiment_id="experiment-1",
            design="randomized", protocol_ref="protocol:experiment-1",
        )
        self.assertTrue(after_restart["already_registered"])

    def test_concurrent_experiment_registration_is_idempotent(self):
        self._propose(self._report())
        self.reviews.decide(
            "review-1", decision_id="decision-1", decision="approved",
            rationale="Approved for a separately controlled evaluation.",
            authorization_ref="human-approval:42",
        )
        root = Path(self.tmp.name)
        barrier = threading.Barrier(2)

        def register(_):
            # SQLite connections must be created, used and closed in the
            # worker thread that owns them.
            reviews = StrategySelfReviewStore(root / "reviews.db")
            causal = CausalExperimentStore(root / "causal.db")
            try:
                barrier.wait(timeout=5)
                return reviews.register_approved_experiment(
                    "review-1", causal, experiment_id="experiment-1",
                    design="randomized", protocol_ref="protocol:experiment-1",
                )
            finally:
                reviews.close()
                causal.close()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(register, range(2)))

        self.assertEqual(1, sum(not item["already_registered"] for item in results))
        self.assertEqual(1, sum(item["already_registered"] for item in results))
        self.assertEqual(1, sum(item["experiment_definition_created"] for item in results))
        self.assertEqual(1, sum(not item["experiment_definition_created"] for item in results))

        # Both independent callers converge on one durable review link and
        # one causal definition; a later retry remains idempotent as well.
        self.assertEqual("conservative-v2", self.causal.experiment("experiment-1")["treatment_name"])
        replay = self.reviews.register_approved_experiment(
            "review-1", self.causal, experiment_id="experiment-1",
            design="randomized", protocol_ref="protocol:experiment-1",
        )
        self.assertTrue(replay["already_registered"])
        self.assertFalse(replay["experiment_definition_created"])

    def test_history_survives_restart(self):
        self._propose(self._report())
        self.reviews.close()
        self.reviews = StrategySelfReviewStore(
            Path(self.tmp.name) / "reviews.db"
        )
        self.assertEqual("proposed", self.reviews.history()[0]["status"])


if __name__ == "__main__":
    unittest.main()
