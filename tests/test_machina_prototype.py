from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from examples.machina_prototype import MachinaPrototype


class MachinaPrototypeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_remember_and_recall_persist_across_restart(self):
        with MachinaPrototype(self.path) as prototype:
            saved = prototype.remember(
                "MNN precisa preservar memórias importantes",
                importance=0.95,
                tags=["mnn", "memoria", "importante"],
            )
            self.assertTrue(saved["id"])
            matches = prototype.recall("memoria importante")
            self.assertEqual([saved["id"]], [item["id"] for item in matches])

        with MachinaPrototype(self.path) as restarted:
            matches = restarted.recall("mnn")
            self.assertEqual([saved["id"]], [item["id"] for item in matches])
            self.assertEqual(1, restarted.status()["memory_fragments"])

    def test_think_runs_auditable_virtual_brain_cycle_with_mnn_signal(self):
        with MachinaPrototype(self.path) as prototype:
            result = prototype.think("Precisamos testar a memória persistente")
            self.assertEqual("completed", result["status"])
            self.assertTrue(result["audit_valid"])
            self.assertIn("activations", result["mnn_signal"])
            self.assertIn("timestep", result["mnn_signal"])
            self.assertIn("interpretation", result["mnn_signal"])

    def test_recall_empty_query_returns_active_memory_view(self):
        with MachinaPrototype(self.path) as prototype:
            prototype.remember("Primeiro fragmento", tags=["primeiro"])
            prototype.remember("Segundo fragmento", tags=["segundo"])
            self.assertEqual(2, len(prototype.recall("")))


if __name__ == "__main__":
    unittest.main()
