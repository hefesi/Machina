from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from machina.experiment_harness import ExperimentHarness, ExperimentSpec
from machina.experiment_ledger import ExperimentLedger, ExperimentLedgerError


class ExperimentLedgerTests(unittest.TestCase):
    def make_record(self):
        spec = ExperimentSpec(
            experiment_id="ledger-trial-1",
            hypothesis_id="H4-continuity",
            condition="restored",
            seed=7,
            input_data={"observation": "resume", "objective": "continue"},
            configuration={"snapshot": "v1"},
            code_revision="abc123",
            budget={"cycles": 1},
        )
        return ExperimentHarness().run(
            spec, lambda _: {"metrics": {"continuity": 1.0}, "status": "completed"}
        )

    def test_append_is_durable_verifiable_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = ExperimentLedger(Path(directory) / "trials.jsonl")
            record = self.make_record()
            self.assertTrue(ledger.append(record))
            self.assertFalse(ledger.append(record))
            self.assertEqual(
                {"valid": True, "record_count": 1, "unique_experiment_count": 1},
                ledger.verify(),
            )
            reopened = ExperimentLedger(ledger.path)
            self.assertEqual(1, len(reopened.records))

    def test_detects_modified_record(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "trials.jsonl"
            ledger = ExperimentLedger(path)
            ledger.append(self.make_record())
            item = json.loads(path.read_text(encoding="utf-8"))
            item["metrics"]["continuity"] = 0.0
            path.write_text(json.dumps(item) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ExperimentLedgerError, "hash mismatch"):
                ExperimentLedger(path)


if __name__ == "__main__":
    unittest.main()
