"""Record evidence-backed changes in Machina's operational self-model."""
from __future__ import annotations

from typing import Any, Mapping

from .contracts import Artifact, ContractKind
from .event_store import EventStore
from .self_model import SelfModel


class SelfTransformationTracker:
    """Compare SelfModel snapshots and journal only actual, traceable changes."""

    def __init__(self, event_store: EventStore) -> None:
        if not isinstance(event_store, EventStore):
            raise TypeError("event_store must be an EventStore")
        self.event_store = event_store

    @staticmethod
    def _diff(previous: Mapping[str, Any], current: Mapping[str, Any]) -> dict[str, Any]:
        changes: dict[str, Any] = {}
        for section in (
            "beliefs", "capability_estimates", "known_limitations", "resource_state"
        ):
            old = previous.get(section)
            new = current.get(section)
            if old != new:
                changes[section] = {"previous": old, "current": new}
        return changes

    def record(
        self,
        previous: SelfModel | Mapping[str, Any],
        current: SelfModel | Mapping[str, Any],
        *,
        cycle_id: str,
        trigger: str,
        evidence_refs: list[str] | tuple[str, ...],
        causation_id: str | None = None,
    ) -> dict[str, Any]:
        """Journal a transformation; snapshots are compared, never mutated."""
        before = previous.snapshot() if isinstance(previous, SelfModel) else dict(previous)
        after = current.snapshot() if isinstance(current, SelfModel) else dict(current)
        if before.get("schema_version") != after.get("schema_version"):
            raise ValueError("self-model schema versions must match")
        if before.get("schema_version") != SelfModel.schema_version:
            raise ValueError("unsupported self-model snapshot schema")
        if not isinstance(cycle_id, str) or not cycle_id.strip():
            raise ValueError("cycle_id must be a non-empty string")
        if not isinstance(trigger, str) or not trigger.strip():
            raise ValueError("trigger must be a non-empty string")
        if isinstance(evidence_refs, (str, bytes)) or not isinstance(evidence_refs, (list, tuple)):
            raise ValueError("evidence_refs must be a sequence of non-empty strings")
        refs = list(dict.fromkeys(evidence_refs))
        if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ValueError("evidence_refs must contain non-empty strings")
        changes = self._diff(before, after)
        if not changes:
            return {
                "changed": False,
                "event_id": None,
                "changes": {},
                "reason": "No operational self-model fields changed.",
            }
        if not self.event_store.has_cycle(cycle_id):
            raise ValueError(f"unknown event-store cycle: {cycle_id}")
        previous_cycle = before.get("cycle_id")
        artifact = Artifact.create(
            ContractKind.MODEL_UPDATE,
            cycle_id=cycle_id,
            producer="SelfTransformationTracker",
            data={
                "target": "SelfModel",
                "previous_version": str(previous_cycle or "uninitialized"),
                "new_version": str(after.get("cycle_id") or cycle_id),
                "change": {
                    "trigger": trigger.strip(),
                    "sections": changes,
                },
                "evidence_refs": refs,
                "reason": "Operational self-model changed between recorded snapshots.",
                "created_by": "SelfTransformationTracker",
            },
            input_refs=refs,
            source_refs=refs,
            epistemic_status="inferred",
            confidence=0.8 if refs else 0.4,
        )
        stored = self.event_store.append(
            "self.transformed", artifact, causation_id=causation_id
        )
        return {
            "changed": True,
            "event_id": stored.event_id,
            "event_hash": stored.event_hash,
            "sequence": stored.sequence,
            "changes": changes,
            "evidence_refs": refs,
            "epistemic_status": artifact.epistemic_status,
        }
