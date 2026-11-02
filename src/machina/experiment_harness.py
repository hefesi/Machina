"""Reproducible, append-only harness for controlled Machina experiments.

The harness records functional evidence. It does not score or claim phenomenal
consciousness, and it never changes agent policy or executes agent actions itself.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Callable, Mapping


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _json_value(value: Any, field: str) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be finite JSON-compatible data") from exc


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ExperimentSpec:
    """Pre-registered trial configuration, captured before execution."""

    experiment_id: str
    hypothesis_id: str
    condition: str
    seed: int
    input_data: Mapping[str, Any]
    configuration: Mapping[str, Any]
    code_revision: str
    budget: Mapping[str, int]

    def __post_init__(self) -> None:
        for name in ("experiment_id", "hypothesis_id", "condition", "code_revision"):
            _text(getattr(self, name), name)
        if isinstance(self.seed, bool) or not isinstance(self.seed, int):
            raise ValueError("seed must be an integer")
        for field_name in ("input_data", "configuration", "budget"):
            if not isinstance(getattr(self, field_name), Mapping):
                raise ValueError(f"{field_name} must be a mapping")
            _json_value(dict(getattr(self, field_name)), field_name)
        for key, value in self.budget.items():
            _text(key, "budget key")
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("budget values must be non-negative integers")

    def snapshot(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis_id": self.hypothesis_id,
            "condition": self.condition,
            "seed": self.seed,
            "input_data": _json_value(dict(self.input_data), "input_data"),
            "configuration": _json_value(dict(self.configuration), "configuration"),
            "code_revision": self.code_revision,
            "budget": _json_value(dict(self.budget), "budget"),
        }

    @property
    def fingerprint(self) -> str:
        return _digest(self.snapshot())


@dataclass(frozen=True)
class TrialRecord:
    """Immutable record of a pre-registered trial and its observed metrics."""

    spec: dict[str, Any]
    spec_fingerprint: str
    metrics: dict[str, float]
    outcome: dict[str, Any]
    record_hash: str

    def snapshot(self) -> dict[str, Any]:
        return {
            "spec": _json_value(self.spec, "spec"),
            "spec_fingerprint": self.spec_fingerprint,
            "metrics": dict(self.metrics),
            "outcome": _json_value(self.outcome, "outcome"),
            "record_hash": self.record_hash,
        }


class ExperimentHarness:
    """Run controlled callbacks and retain immutable, reproducible trial records.

    The callback is supplied by the experiment/test, so this class does not
    couple itself to a particular Machina runtime or grant action permissions.
    """

    def __init__(self) -> None:
        self._records: dict[str, TrialRecord] = {}

    @property
    def records(self) -> tuple[TrialRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def run(
        self,
        spec: ExperimentSpec,
        execute: Callable[[ExperimentSpec], Mapping[str, Any]],
    ) -> TrialRecord:
        if not isinstance(spec, ExperimentSpec):
            raise ValueError("spec must be an ExperimentSpec")
        if not callable(execute):
            raise ValueError("execute must be callable")
        existing = self._records.get(spec.experiment_id)
        if existing is not None:
            if existing.spec_fingerprint != spec.fingerprint:
                raise ValueError("experiment_id already exists with a different specification")
            return existing

        raw = execute(spec)
        if not isinstance(raw, Mapping):
            raise ValueError("experiment callback must return a mapping")
        raw_metrics = raw.get("metrics", {})
        if not isinstance(raw_metrics, Mapping):
            raise ValueError("metrics must be a mapping")
        metrics: dict[str, float] = {}
        for raw_name, raw_value in raw_metrics.items():
            name = _text(raw_name, "metric name")
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ValueError(f"metric {name!r} must be numeric")
            value = float(raw_value)
            if not math.isfinite(value):
                raise ValueError(f"metric {name!r} must be finite")
            metrics[name] = value
        outcome = _json_value(
            {key: value for key, value in raw.items() if key != "metrics"},
            "outcome",
        )
        spec_snapshot = spec.snapshot()
        payload = {
            "spec": spec_snapshot,
            "spec_fingerprint": spec.fingerprint,
            "metrics": metrics,
            "outcome": outcome,
        }
        record = TrialRecord(
            spec=spec_snapshot,
            spec_fingerprint=spec.fingerprint,
            metrics=metrics,
            outcome=outcome,
            record_hash=_digest(payload),
        )
        self._records[spec.experiment_id] = record
        return record

    def compare(
        self,
        baseline_id: str,
        treatment_id: str,
        metric: str,
    ) -> dict[str, Any]:
        """Return a transparent treatment-minus-baseline paired trial delta."""
        baseline = self._get(baseline_id)
        treatment = self._get(treatment_id)
        if baseline.spec["hypothesis_id"] != treatment.spec["hypothesis_id"]:
            raise ValueError("trials must belong to the same hypothesis")
        if baseline.spec["seed"] != treatment.spec["seed"]:
            raise ValueError("paired trials must use the same seed")
        if baseline.spec["input_data"] != treatment.spec["input_data"]:
            raise ValueError("paired trials must use identical input_data")
        if baseline.spec["budget"] != treatment.spec["budget"]:
            raise ValueError("paired trials must use identical budgets")
        if metric not in baseline.metrics or metric not in treatment.metrics:
            raise ValueError(f"metric {metric!r} must exist in both trials")
        return {
            "hypothesis_id": baseline.spec["hypothesis_id"],
            "baseline_id": baseline_id,
            "treatment_id": treatment_id,
            "metric": metric,
            "baseline": baseline.metrics[metric],
            "treatment": treatment.metrics[metric],
            "delta_treatment_minus_baseline": (
                treatment.metrics[metric] - baseline.metrics[metric]
            ),
            "interpretation": "descriptive_only",
        }

    def to_jsonl(self) -> str:
        """Export stable JSONL; callers choose the durable storage destination."""
        return "".join(
            json.dumps(record.snapshot(), sort_keys=True, separators=(",", ":"), allow_nan=False)
            + "\n"
            for record in self.records
        )

    def _get(self, experiment_id: str) -> TrialRecord:
        key = _text(experiment_id, "experiment_id")
        try:
            return self._records[key]
        except KeyError as exc:
            raise KeyError(f"unknown experiment_id: {key}") from exc
