"""Durable JSONL ledger for immutable experiment trial records.

The ledger provides integrity checking and process-local idempotency. It is
not a distributed lock or a substitute for backing up the destination file.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from .experiment_harness import TrialRecord


class ExperimentLedgerError(ValueError):
    """Raised when a ledger is malformed or a trial conflicts with history."""


def _canonical_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), allow_nan=False
    )
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class ExperimentLedger:
    """Append-only JSONL persistence with record-hash verification."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records = self._read_and_verify()

    @property
    def records(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(item) for item in self._records)

    def append(self, record: TrialRecord) -> bool:
        """Append a record; return False for an identical already-stored trial."""
        if not isinstance(record, TrialRecord):
            raise TypeError("record must be a TrialRecord")
        snapshot = record.snapshot()
        experiment_id = snapshot["spec"]["experiment_id"]
        existing = next(
            (item for item in self._records
             if item["spec"]["experiment_id"] == experiment_id),
            None,
        )
        if existing is not None:
            if existing["spec_fingerprint"] != snapshot["spec_fingerprint"]:
                raise ExperimentLedgerError(
                    "experiment_id already exists with a different specification"
                )
            if existing["record_hash"] != snapshot["record_hash"]:
                raise ExperimentLedgerError(
                    "experiment_id already exists with a different result"
                )
            return False

        line = json.dumps(
            snapshot, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(line + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self._records.append(snapshot)
        return True

    def verify(self) -> dict[str, Any]:
        """Re-read disk and report verified record count and unique trial IDs."""
        records = self._read_and_verify()
        return {
            "valid": True,
            "record_count": len(records),
            "unique_experiment_count": len({
                item["spec"]["experiment_id"] for item in records
            }),
        }

    def _read_and_verify(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        seen: dict[str, dict[str, Any]] = {}
        with self.path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    raise ExperimentLedgerError(
                        f"blank line at ledger line {line_number}"
                    )
                try:
                    item = json.loads(line)
                    payload = {
                        key: item[key]
                        for key in ("spec", "spec_fingerprint", "metrics", "outcome")
                    }
                    expected_hash = _canonical_hash(payload)
                    experiment_id = item["spec"]["experiment_id"]
                except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                    raise ExperimentLedgerError(
                        f"invalid ledger record at line {line_number}"
                    ) from exc
                if item.get("record_hash") != expected_hash:
                    raise ExperimentLedgerError(
                        f"record hash mismatch at line {line_number}"
                    )
                previous = seen.get(experiment_id)
                if previous is not None:
                    if previous["record_hash"] != item["record_hash"]:
                        raise ExperimentLedgerError(
                            f"conflicting duplicate experiment at line {line_number}"
                        )
                    raise ExperimentLedgerError(
                        f"duplicate experiment at line {line_number}"
                    )
                seen[experiment_id] = item
                records.append(item)
        return records
