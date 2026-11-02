from __future__ import annotations

import unittest

from machina.experiment_harness import ExperimentHarness
from machina.self_continuity_ablation import run_commitment_alignment_ablation


class CommitmentAlignmentAblationTests(unittest.TestCase):
    def test_commitment_feedback_changes_selection_with_same_identity_record(self):
        result = run_commitment_alignment_ablation(
            ExperimentHarness(),
            hypothesis_id="H-self-continuity-policy",
            code_revision="test-revision",
            seed=13,
        )
        off = result["trials"]["commitment_signal_off"]
        on = result["trials"]["commitment_signal_on"]
        self.assertEqual("goal_a", off["outcome"]["decision"]["selected_goal"]["goal_id"])
        self.assertEqual("goal_b", on["outcome"]["decision"]["selected_goal"]["goal_id"])
        self.assertEqual(
            off["outcome"]["continuity"],
            on["outcome"]["continuity"],
        )
        self.assertEqual(1.0, result["comparison"]["delta_treatment_minus_baseline"])

    def test_rejects_invalid_seed(self):
        with self.assertRaisesRegex(ValueError, "seed"):
            run_commitment_alignment_ablation(
                ExperimentHarness(),
                hypothesis_id="H-self",
                code_revision="test",
                seed=True,
            )


if __name__ == "__main__":
    unittest.main()
