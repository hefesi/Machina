from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from benchmarks.fragment_memory_retrieval import run_benchmark


class FragmentMemoryEvaluationTests(unittest.TestCase):
    def test_decay_archive_retrieval_and_reinforcement_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_benchmark(Path(directory) / "fragments.sqlite3")

        self.assertTrue(result["passed"], result)
        active = result["active_view_before_reinforcement"]
        archive = result["archive_before_reinforcement"]
        retrieval = result["lexical_retrieval_probe"]
        reinforcement = result["reinforcement_probe"]
        after = result["archive_after_reinforcement"]

        self.assertFalse(active["aged_rule_in_active_view"])
        self.assertTrue(archive["aged_rule_present"])
        self.assertEqual(3, archive["count"])
        self.assertEqual(0, retrieval["result_count"])
        self.assertTrue(retrieval["direct_lookup_succeeded"])
        self.assertTrue(reinforcement["pinned"])
        self.assertEqual("aged-important-rule", reinforcement["active_top_id"])
        self.assertTrue(after["ids_unchanged"])
        self.assertEqual(3, after["count"])


if __name__ == "__main__":
    unittest.main()
