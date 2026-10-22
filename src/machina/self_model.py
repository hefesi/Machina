"""Evidence-grounded, serializable self-model for Machina.

Tracks operational beliefs and capability estimates. This module does not infer
consciousness from self-reports and has no side effects on MNN weights or actions.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from typing import Any

_SCHEMA_VERSION = 1
_STATUSES = {"observed", "inferred", "stale", "unknown"}


def _name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _confidence(value: Any, field: str = "confidence") -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field} must be finite and in [0, 1]")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be finite and in [0, 1]") from exc
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError(f"{field} must be finite and in [0, 1]")
    return result


def _json_copy(value: Any, field: str) -> Any:
    try:
        return json.loads(json.dumps(value, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be JSON-compatible and finite") from exc


class SelfModel:
    """Persistent model of operational state, evidence, limits, and capabilities."""

    schema_version = _SCHEMA_VERSION

    def __init__(self) -> None:
        self._beliefs: dict[str, dict[str, Any]] = {}
        self._capabilities: dict[str, dict[str, Any]] = {}
        self._limitations: list[str] = []
        self._resources: dict[str, Any] = {}
        self._prediction_errors: list[dict[str, Any]] = []
        self._cycle_id: str | None = None

    @property
    def beliefs(self) -> dict[str, dict[str, Any]]:
        return _json_copy(self._beliefs, "beliefs")

    @property
    def capability_estimates(self) -> dict[str, dict[str, Any]]:
        return _json_copy(self._capabilities, "capability_estimates")

    @property
    def known_limitations(self) -> list[str]:
        return list(self._limitations)

    @property
    def resource_state(self) -> dict[str, Any]:
        return _json_copy(self._resources, "resource_state")

    @property
    def prediction_errors(self) -> list[dict[str, Any]]:
        return _json_copy(self._prediction_errors, "prediction_errors")

    @property
    def cycle_id(self) -> str | None:
        return self._cycle_id

    def update(
        self,
        observations: Mapping[str, Any],
        *,
        cycle_id: str,
        evidence_refs: Mapping[str, str] | None = None,
        statuses: Mapping[str, str] | None = None,
        confidences: Mapping[str, float] | None = None,
        capability_estimates: Mapping[str, Mapping[str, Any]] | None = None,
        known_limitations: Sequence[str] | None = None,
        resource_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update beliefs; unsupported observations default to unknown, not fact."""
        if not isinstance(observations, Mapping):
            raise ValueError("observations must be a mapping")
        cycle = _name(cycle_id, "cycle_id")
        refs, requested_statuses, requested_confidences = (
            evidence_refs or {}, statuses or {}, confidences or {}
        )

        for raw_prop, raw_value in observations.items():
            prop = _name(raw_prop, "observation property")
            status = requested_statuses.get(prop)
            if status is None:
                status = "observed" if refs.get(prop) else "unknown"
            if status not in _STATUSES:
                raise ValueError(f"invalid status for {prop!r}")
            evidence = refs.get(prop)
            if evidence is not None:
                evidence = _name(evidence, f"evidence reference for {prop}")
            if status == "observed" and not evidence:
                raise ValueError(f"observed belief {prop!r} requires evidence_ref")
            if status == "unknown":
                value, confidence, evidence = None, 0.0, None
            else:
                value = _json_copy(raw_value, f"observation {prop}")
                default = 1.0 if status == "observed" else 0.5
                confidence = _confidence(requested_confidences.get(prop, default), prop)
            self._beliefs[prop] = {
                "property": prop, "value": value, "confidence": confidence,
                "evidence_ref": evidence, "observed_at_cycle": cycle, "status": status,
            }

        if capability_estimates is not None:
            if not isinstance(capability_estimates, Mapping):
                raise ValueError("capability_estimates must be a mapping")
            for raw_name, raw_item in capability_estimates.items():
                name = _name(raw_name, "capability name")
                if not isinstance(raw_item, Mapping):
                    raise ValueError(f"capability {name!r} must be a mapping")
                status = raw_item.get("status", "unknown")
                if status not in _STATUSES:
                    raise ValueError(f"invalid status for capability {name!r}")
                evidence = raw_item.get("evidence_ref")
                if evidence is not None:
                    evidence = _name(evidence, "capability evidence_ref")
                if status == "observed" and not evidence:
                    raise ValueError(f"observed capability {name!r} requires evidence_ref")
                if status == "unknown":
                    estimate, confidence, evidence = None, 0.0, None
                else:
                    if "estimate" not in raw_item:
                        raise ValueError(f"capability {name!r} requires estimate")
                    estimate = _json_copy(raw_item["estimate"], f"capability {name}")
                    default = 1.0 if status == "observed" else 0.5
                    confidence = _confidence(raw_item.get("confidence", default), name)
                self._capabilities[name] = {
                    "estimate": estimate, "confidence": confidence,
                    "evidence_ref": evidence, "observed_at_cycle": cycle, "status": status,
                }

        if known_limitations is not None:
            if isinstance(known_limitations, (str, bytes)):
                raise ValueError("known_limitations must be a sequence of strings")
            self._limitations = list(dict.fromkeys(
                _name(item, "known limitation") for item in known_limitations
            ))
        if resource_state is not None:
            if not isinstance(resource_state, Mapping):
                raise ValueError("resource_state must be a mapping")
            self._resources = _json_copy(dict(resource_state), "resource_state")
        self._cycle_id = cycle
        return self.snapshot()

    def mark_unknown(self, property_name: str, *, cycle_id: str) -> dict[str, Any]:
        """Invalidate a belief when its current value cannot be established."""
        return self.update(
            {property_name: None}, cycle_id=cycle_id,
            statuses={property_name: "unknown"},
        )

    def record_prediction_error(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Append an evaluated prediction record; existing records are never replaced."""
        if not isinstance(record, Mapping):
            raise ValueError("prediction error record must be a mapping")
        item = _json_copy(dict(record), "prediction error record")
        if not item or "prediction_ref" not in item or "error" not in item:
            raise ValueError("prediction error record requires prediction_ref and error")
        item["prediction_ref"] = _name(item["prediction_ref"], "prediction_ref")
        self._prediction_errors.append(item)
        return _json_copy(item, "prediction error record")

    def snapshot(self) -> dict[str, Any]:
        """Return a detached JSON-compatible snapshot."""
        return {
            "schema_version": _SCHEMA_VERSION,
            "cycle_id": self._cycle_id,
            "beliefs": _json_copy(self._beliefs, "beliefs"),
            "capability_estimates": _json_copy(self._capabilities, "capability_estimates"),
            "known_limitations": list(self._limitations),
            "resource_state": _json_copy(self._resources, "resource_state"),
            "prediction_errors": _json_copy(self._prediction_errors, "prediction_errors"),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping[str, Any]) -> "SelfModel":
        """Restore a validated snapshot, rejecting unsupported schema versions."""
        if not isinstance(data, Mapping):
            raise ValueError("snapshot must be a mapping")
        if data.get("schema_version") != _SCHEMA_VERSION:
            raise ValueError("unsupported SelfModel snapshot schema_version")
        required = {
            "cycle_id", "beliefs", "capability_estimates", "known_limitations",
            "resource_state", "prediction_errors",
        }
        missing = required - set(data)
        if missing:
            raise ValueError(f"snapshot missing fields: {sorted(missing)}")
        model = cls()
        if data["cycle_id"] is not None:
            model._cycle_id = _name(data["cycle_id"], "cycle_id")

        beliefs = data["beliefs"]
        if not isinstance(beliefs, Mapping):
            raise ValueError("snapshot beliefs must be a mapping")
        for raw_prop, raw_belief in beliefs.items():
            prop = _name(raw_prop, "belief property")
            if not isinstance(raw_belief, Mapping) or raw_belief.get("property") != prop:
                raise ValueError(f"invalid belief record for {prop!r}")
            status = raw_belief.get("status")
            if status not in _STATUSES:
                raise ValueError(f"invalid status for belief {prop!r}")
            confidence = _confidence(raw_belief.get("confidence"), prop)
            value = _json_copy(raw_belief.get("value"), f"belief {prop}")
            evidence = raw_belief.get("evidence_ref")
            if status == "observed":
                evidence = _name(evidence, "evidence_ref")
            if status == "unknown" and (value is not None or confidence != 0):
                raise ValueError(f"unknown belief {prop!r} must have null value and zero confidence")
            model._beliefs[prop] = {
                "property": prop, "value": value, "confidence": confidence,
                "evidence_ref": evidence,
                "observed_at_cycle": _name(raw_belief.get("observed_at_cycle"), "observed_at_cycle"),
                "status": status,
            }

        capabilities = data["capability_estimates"]
        if not isinstance(capabilities, Mapping):
            raise ValueError("snapshot capability_estimates must be a mapping")
        for raw_name, raw_item in capabilities.items():
            name = _name(raw_name, "capability name")
            if not isinstance(raw_item, Mapping):
                raise ValueError(f"invalid capability record for {name!r}")
            status = raw_item.get("status")
            if status not in _STATUSES:
                raise ValueError(f"invalid status for capability {name!r}")
            confidence = _confidence(raw_item.get("confidence"), "capability confidence")
            evidence = raw_item.get("evidence_ref")
            if status == "observed":
                evidence = _name(evidence, "capability evidence_ref")
            estimate = _json_copy(raw_item.get("estimate"), f"capability {name}")
            if status == "unknown" and (estimate is not None or confidence != 0):
                raise ValueError(f"unknown capability {name!r} must have null estimate and zero confidence")
            model._capabilities[name] = {
                "estimate": estimate, "confidence": confidence, "evidence_ref": evidence,
                "observed_at_cycle": _name(raw_item.get("observed_at_cycle"), "capability observed_at_cycle"),
                "status": status,
            }

        limitations = data["known_limitations"]
        if not isinstance(limitations, list):
            raise ValueError("snapshot known_limitations must be a list")
        model._limitations = [_name(item, "known limitation") for item in limitations]
        if not isinstance(data["resource_state"], Mapping):
            raise ValueError("snapshot resource_state must be a mapping")
        model._resources = _json_copy(dict(data["resource_state"]), "resource_state")
        errors = data["prediction_errors"]
        if not isinstance(errors, list):
            raise ValueError("snapshot prediction_errors must be a list")
        for raw_record in errors:
            if not isinstance(raw_record, Mapping):
                raise ValueError("prediction error entries must be mappings")
            record = _json_copy(dict(raw_record), "prediction error")
            if "prediction_ref" not in record or "error" not in record:
                raise ValueError("prediction error record requires prediction_ref and error")
            record["prediction_ref"] = _name(record["prediction_ref"], "prediction_ref")
            model._prediction_errors.append(record)
        return model
