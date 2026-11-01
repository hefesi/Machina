"""D08.2: audit continuity of functional identity across state transitions."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping


def _required(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


@dataclass
class SelfContinuity:
    agent_id: str
    schema_version: int = 1
    commitments: dict[str, str] = field(default_factory=dict)
    event_history: list[dict[str, Any]] = field(default_factory=list)
    component_versions: dict[str, str] = field(default_factory=dict)
    commitment_history: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.agent_id = _required(self.agent_id, "agent_id")
        if not isinstance(self.schema_version, int) or isinstance(self.schema_version, bool) or self.schema_version < 1:
            raise ValueError("schema_version must be a positive integer")
        self.commitments = {
            _required(key, "commitment name"): _required(value, "commitment value")
            for key, value in self.commitments.items()
        }
        self.component_versions = {
            _required(key, "component name"): _required(value, "component version")
            for key, value in self.component_versions.items()
        }
        # Detach caller-owned records so later mutation cannot rewrite history.
        self.event_history = self._json_copy(self.event_history, "event_history")
        self.commitment_history = self._json_copy(self.commitment_history, "commitment_history")

    @staticmethod
    def _json_copy(value: Any, field_name: str) -> Any:
        try:
            return json.loads(json.dumps(value, allow_nan=False))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must contain finite JSON-compatible values") from exc

    def record_event(self, event: str, source: str, *, reason: str = "") -> None:
        event = _required(event, "event")
        source = _required(source, "source")
        if not isinstance(reason, str):
            raise ValueError("reason must be a string")
        self.event_history.append({
            "event": event,
            "source": source,
            "reason": reason,
            "sequence": len(self.event_history) + 1,
        })

    def update_commitment(self, name: str, value: str, *, reason: str, source: str) -> dict[str, Any]:
        """Revise a commitment while retaining its complete append-only history."""
        name = _required(name, "name")
        value = _required(value, "value")
        reason = _required(reason, "reason")
        source = _required(source, "source")
        previous = self.commitments.get(name)
        if previous == value:
            raise ValueError("commitment is unchanged; no revision to record")
        revision = {
            "sequence": len(self.commitment_history) + 1,
            "name": name,
            "previous_value": previous,
            "new_value": value,
            "reason": reason,
            "source": source,
        }
        self.commitment_history.append(revision)
        self.commitments[name] = value
        self.record_event(
            event=f"commitment_changed:{name}:{previous!r}->{value!r}",
            source=source,
            reason=reason,
        )
        return self._json_copy(revision, "commitment revision")

    def retire_commitment(self, name: str, *, reason: str, source: str) -> dict[str, Any]:
        """Retire an active commitment without erasing its revision history."""
        name = _required(name, "name")
        reason = _required(reason, "reason")
        source = _required(source, "source")
        if name not in self.commitments:
            raise ValueError(f"no active commitment named {name!r}")
        previous = self.commitments.pop(name)
        revision = {
            "sequence": len(self.commitment_history) + 1,
            "name": name,
            "previous_value": previous,
            "new_value": None,
            "reason": reason,
            "source": source,
        }
        self.commitment_history.append(revision)
        self.record_event(
            event=f"commitment_retired:{name}:{previous!r}",
            source=source,
            reason=reason,
        )
        return self._json_copy(revision, "commitment retirement")

    def snapshot(self) -> dict[str, Any]:
        """Return a detached, serializable identity/commitment snapshot."""
        return self._json_copy({
            "schema_version": self.schema_version,
            "agent_id": self.agent_id,
            "commitments": self.commitments,
            "event_history": self.event_history,
            "component_versions": self.component_versions,
            "commitment_history": self.commitment_history,
        }, "SelfContinuity snapshot")

    @classmethod
    def from_snapshot(cls, data: Mapping[str, Any]) -> "SelfContinuity":
        if not isinstance(data, Mapping):
            raise ValueError("snapshot must be a mapping")
        required = {
            "schema_version", "agent_id", "commitments", "event_history",
            "component_versions", "commitment_history",
        }
        missing = required - set(data)
        if missing:
            raise ValueError(f"snapshot missing fields: {sorted(missing)}")
        if data["schema_version"] != 1:
            raise ValueError("unsupported SelfContinuity snapshot schema_version")
        for field_name in ("commitments", "component_versions"):
            if not isinstance(data[field_name], Mapping):
                raise ValueError(f"snapshot {field_name} must be a mapping")
        for field_name in ("event_history", "commitment_history"):
            if not isinstance(data[field_name], list):
                raise ValueError(f"snapshot {field_name} must be a list")
        instance = cls(
            agent_id=data["agent_id"],
            schema_version=data["schema_version"],
            commitments=dict(data["commitments"]),
            event_history=data["event_history"],
            component_versions=dict(data["component_versions"]),
            commitment_history=data["commitment_history"],
        )
        for index, item in enumerate(instance.event_history, start=1):
            if not isinstance(item, Mapping) or item.get("sequence") != index:
                raise ValueError("event_history sequence is invalid")
            _required(item.get("event"), "event_history event")
            _required(item.get("source"), "event_history source")
        latest_revisions: dict[str, Any] = {}
        for index, item in enumerate(instance.commitment_history, start=1):
            if not isinstance(item, Mapping) or item.get("sequence") != index:
                raise ValueError("commitment_history sequence is invalid")
            name = _required(item.get("name"), "commitment_history name")
            _required(item.get("reason"), "commitment_history reason")
            _required(item.get("source"), "commitment_history source")
            previous = item.get("previous_value")
            current = item.get("new_value")
            if previous is not None:
                _required(previous, "previous commitment value")
            if current is not None:
                _required(current, "new commitment value")
            latest_revisions[name] = current
        for name, latest_value in latest_revisions.items():
            if latest_value is None:
                if name in instance.commitments:
                    raise ValueError(f"retired commitment {name!r} is still active")
            elif instance.commitments.get(name) != latest_value:
                raise ValueError(f"active commitment {name!r} disagrees with its latest revision")
        return instance

    def continuity_report(self, previous: "SelfContinuity") -> dict[str, Any]:
        return {
            "same_agent_id": self.agent_id == previous.agent_id,
            "same_schema_version": self.schema_version == previous.schema_version,
            "commitments_preserved": {
                key: self.commitments.get(key) == value
                for key, value in previous.commitments.items()
            },
            "history_extends_previous": self.event_history[:len(previous.event_history)] == previous.event_history,
            "commitment_history_extends_previous": (
                self.commitment_history[:len(previous.commitment_history)]
                == previous.commitment_history
            ),
            "component_versions": {
                key: {
                    "previous": previous.component_versions.get(key),
                    "current": self.component_versions.get(key),
                    "changed": previous.component_versions.get(key) != self.component_versions.get(key),
                }
                for key in sorted(set(previous.component_versions) | set(self.component_versions))
            },
        }
