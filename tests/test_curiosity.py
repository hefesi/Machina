import tempfile
import unittest
from pathlib import Path

from machina.curiosity import CuriosityInvestigationStore
from machina.goal_outcome_learning import GoalOutcomeLearner
from machina.self_model import SelfModel
from machina.self_model_learning import SelfModelLearningBridge


class CuriosityInvestigationStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "curiosity.sqlite3"
        self.store = CuriosityInvestigationStore(self.path)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _start(self, investigation_id="inv-1", question="How does recall work?"):
        return self.store.start_investigation(
            investigation_id, gap_property="memory_recall", question=question,
            hypothesis="Indexing quality is a limiting factor",
            selection_reason="High information gain and low risk",
            cycle_id="cycle-1", goal_id="investigate_gap:memory-recall",
        )

    def test_lifecycle_keeps_hypothesis_evidence_and_unknowns_separate(self):
        started = self._start()
        self.assertEqual("open", started["status"])
        self.assertEqual("Indexing quality is a limiting factor", started["hypothesis"])
        self.store.record_evidence(
            "inv-1", evidence_ref="benchmark:recall-1",
            finding="Recall improved on indexed fragments", cycle_id="cycle-2",
        )
        closed = self.store.close_investigation(
            "inv-1", outcome="partially_answered",
            answer_summary="Indexing appears relevant, but the test is limited.",
            remaining_unknowns=["Performance on long histories"],
            cycle_id="cycle-3",
        )
        self.assertEqual("partially_answered", closed["outcome"])
        self.assertEqual(["Performance on long histories"], closed["remaining_unknowns"])
        self.assertEqual("benchmark:recall-1", closed["evidence"][0]["evidence_ref"])
        self.assertEqual("cycle-3", closed["closed_cycle_id"])

    def test_restart_preserves_investigation_and_evidence(self):
        self._start()
        self.store.record_evidence(
            "inv-1", evidence_ref="source:one", finding="Observed result", cycle_id="cycle-2",
        )
        self.store.close()
        self.store = CuriosityInvestigationStore(self.path)
        restored = self.store.get_investigation("inv-1")
        self.assertEqual("open", restored["status"])
        self.assertEqual("Observed result", restored["evidence"][0]["finding"])

    def test_equivalent_open_question_is_blocked_and_prior_history_is_detected(self):
        self._start(question="  How   does RECALL work? ")
        self.assertTrue(self.store.has_prior_question("memory_recall", "how does recall work?"))
        self.assertTrue(self.store.has_open_question("memory_recall", "HOW DOES RECALL WORK?"))
        with self.assertRaisesRegex(ValueError, "equivalent question"):
            self._start("inv-2", question="how does recall work?")

    def test_duplicate_evidence_and_closed_mutations_are_rejected(self):
        self._start()
        self.store.record_evidence(
            "inv-1", evidence_ref="source:one", finding="Finding", cycle_id="cycle-2",
        )
        with self.assertRaisesRegex(ValueError, "already been recorded"):
            self.store.record_evidence(
                "inv-1", evidence_ref="source:one", finding="Changed finding", cycle_id="cycle-3",
            )
        self.store.close_investigation(
            "inv-1", outcome="answered", answer_summary="Question answered.",
            remaining_unknowns=[], cycle_id="cycle-4",
        )
        with self.assertRaisesRegex(ValueError, "already closed"):
            self.store.close_investigation(
                "inv-1", outcome="answered", answer_summary="Rewrite.",
                remaining_unknowns=[], cycle_id="cycle-5",
            )
        with self.assertRaisesRegex(ValueError, "closed investigation"):
            self.store.record_evidence(
                "inv-1", evidence_ref="source:two", finding="Late evidence", cycle_id="cycle-5",
            )
        with self.assertRaisesRegex(ValueError, "already exists"):
            self._start("inv-1", question="A different question")

    def test_bridge_suppresses_questions_already_in_investigation_history(self):
        learner = GoalOutcomeLearner(Path(self.tmp.name) / "outcomes.sqlite3")
        try:
            bridge = SelfModelLearningBridge(SelfModel(), learner)
            mapping = {"memory_recall": {"question": "How does recall work?"}}
            self._start()
            result = bridge.propose_curiosity_goals(mapping, investigation_store=self.store)
            self.assertEqual([], result["goals"])
            self.assertEqual("prior_investigation_exists", result["suppressed"][0]["reason"])
            repeated = bridge.propose_curiosity_goals(
                mapping, investigation_store=self.store, allow_repeat=True,
            )
            self.assertEqual(1, len(repeated["goals"]))
            self.assertFalse(repeated["goals"][0].requires_external_action)
        finally:
            learner.close()

    def test_invalid_lifecycle_data_is_rejected(self):
        self._start()
        with self.assertRaisesRegex(ValueError, "outcome must be"):
            self.store.close_investigation(
                "inv-1", outcome="unknown", answer_summary="No result",
                remaining_unknowns=["More work"], cycle_id="cycle-2",
            )
        with self.assertRaisesRegex(ValueError, "remaining_unknowns"):
            self.store.close_investigation(
                "inv-1", outcome="unanswered", answer_summary="No result",
                remaining_unknowns="not a list", cycle_id="cycle-2",
            )
        self.assertEqual("open", self.store.get_investigation("inv-1")["status"])


if __name__ == "__main__":
    unittest.main()
