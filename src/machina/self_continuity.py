"""D08.2: audit continuity of functional identity across state transitions."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SelfContinuity:
    agent_id: str
    schema_version: int = 1
    commitments: dict[str, str] = field(default_factory=dict)
    event_history: list[dict[str, Any]] = field(default_factory=list)
    component_versions: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.agent_id.strip():
            raise ValueError("agent_id must be non-empty")
        if self.schema_version < 1:
            raise ValueError("schema_version must be positive")

    def record_event(self, event: str, source: str, *, reason: str = "") -> None:
        if not event.strip() or not source.strip():
            raise ValueError("event and source must be non-empty")
        self.event_history.append({
            "event": event,
            "source": source,
            "reason": reason,
            "sequence": len(self.event_history) + 1,
        })

    def update_commitment(self, name: str, value: str, *, reason: str, source: str) -> None:
        if not name.strip() or not value.strip() or not reason.strip() or not source.strip():
            raise ValueError("name, value, reason and source must be non-empty")
        previous = self.commitments.get(name)
        self.commitments[name] = value
        self.record_event(
            event=f"commitment_changed:{name}:{previous!r}->{value!r}",
            source=source,
            reason=reason,
        )

    def continuity_report(self, previous: "SelfContinuity") -> dict[str, Any]:
        return {
            "same_agent_id": self.agent_id == previous.agent_id,
            "same_schema_version": self.schema_version == previous.schema_version,
            "commitments_preserved": {
                key: self.commitments.get(key) == value
                for key, value in previous.commitments.items()
            },
            "history_extends_previous": self.event_history[:len(previous.event_history)] == previous.event_history,
            "component_versions": {
                key: {
                    "previous": previous.component_versions.get(key),
                    "current": self.component_versions.get(key),
                    "changed": previous.component_versions.get(key) != self.component_versions.get(key),
                }
                for key in sorted(set(previous.component_versions) | set(self.component_versions))
            },
        }
