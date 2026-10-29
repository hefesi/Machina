import tempfile
import unittest
from pathlib import Path

from benchmarks.mnn_persistent_adaptation import run_benchmark


class MNNPersistentAdaptationBenchmarkTests(unittest.TestCase):
    def test_learns_adapts_and_retains_state_and_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = run_benchmark(
                state_path=root / "state" / "learner.json",
                memory_path=root / "memory" / "experiences.sqlite3",
            )
        self.assertTrue(result["passed"], result)
        self.assertGreater(
            result["phase_1"]["predictions"]["left"],
            result["phase_1"]["predictions"]["right"],
        )
        self.assertGreater(
            result["phase_2"]["predictions"]["right"],
            result["phase_2"]["predictions"]["left"],
        )
        self.assertTrue(result["restart"]["learner_state_preserved"])
        self.assertTrue(result["persistent_memory"]["environment_shift_recalled"])
        self.assertEqual(result["persistent_memory"]["archive_count_after_reopen"], 2)

    def test_rejects_too_short_phase(self):
        with self.assertRaises(ValueError):
            run_benchmark(rounds_per_phase=9)


if __name__ == "__main__":
    unittest.main()
