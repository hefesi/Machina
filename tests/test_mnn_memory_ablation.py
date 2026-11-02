from __future__ import annotations

import unittest

from machina.experiment_harness import ExperimentHarness
from machina.mnn_memory_ablation import run_memory_guidance_ablation


class MNNMemoryAblationTests(unittest.TestCase):
    def test_real_memory_route_ablation_changes_neural_input_and_activation(self):
        result = run_memory_guidance_ablation(
            ExperimentHarness(),
            hypothesis_id="H5-memory-route",
            code_revision="test-revision",
            observation="The machine learned from a prior prediction error.",
            query="prior prediction error",
            seed=7,
        )
        off = result["trials"]["memory_path_off"]
        on = result["trials"]["memory_path_on"]
        self.assertFalse(off["outcome"]["intervention"]["retrieval_to_neural_route_enabled"])
        self.assertTrue(on["outcome"]["intervention"]["retrieval_to_neural_route_enabled"])
        self.assertEqual(0.0, off["metrics"]["memory_signal"])
        self.assertGreater(on["metrics"]["memory_signal"], 0.0)
        self.assertGreater(on["metrics"]["retrieved_evidence_count"], 0.0)
        self.assertNotEqual(
            off["metrics"]["integrator_activation"],
            on["metrics"]["integrator_activation"],
        )
        self.assertEqual("descriptive_mechanistic_ablation", result["interpretation"])

    def test_rejects_empty_query(self):
        with self.assertRaisesRegex(ValueError, "query"):
            run_memory_guidance_ablation(
                ExperimentHarness(),
                hypothesis_id="H5",
                code_revision="test",
                observation="prior event",
                query=" ",
            )


if __name__ == "__main__":
    unittest.main()
