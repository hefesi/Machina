from __future__ import annotations

import unittest

from examples.autonomy_d25_confidence_demo import run_demo
from machina.confidence_policy import decide
from machina.transfer_benchmark import TRANSFER_TASKS, TransferTask


class ConfidencePolicyTests(unittest.TestCase):
    def test_supported_tasks_are_answered_correctly(self):
        for task in TRANSFER_TASKS:
            with self.subTest(task=task.task_type):
                decision = decide(task)
                self.assertEqual("answered", decision.status)
                self.assertEqual(task.expected_answer, decision.answer)
                self.assertEqual(1.0, decision.confidence)

    def test_conflicting_values_force_abstention(self):
        task = TransferTask(
            "ambiguous",
            "- Ivo — editor: Helix\n- Ivo — editor: Vim",
            "Find editor belonging to Ivo.",
            "not used",
        )
        decision = decide(task)
        self.assertIsNone(decision.answer)
        self.assertEqual("abstained_ambiguous", decision.status)
        self.assertEqual({"Helix", "Vim"}, set(decision.candidates))

    def test_missing_evidence_forces_abstention(self):
        task = TransferTask(
            "unsupported",
            "A free-form note mentions Ivo and Helix without a field assignment.",
            "Find editor belonging to Ivo.",
            "not used",
        )
        decision = decide(task)
        self.assertIsNone(decision.answer)
        self.assertEqual("abstained_no_evidence", decision.status)

    def test_demo_passes(self):
        self.assertTrue(run_demo()["passed"])


if __name__ == "__main__":
    unittest.main()
