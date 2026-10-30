"""Reconstruct a traceable operational autobiography from the event journal.

This is a read-only projection: the append-only EventStore remains the source
of truth, and the projection makes no claim about phenomenal experience.
"""
from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from .event_store import EventStore


class SelfAutobiography:
    """Read-only chronological account of recorded events and their provenance."""

    def __init__(self, event_store: EventStore) -> None:
        if not isinstance(event_store, EventStore):
            raise TypeError("event_store must be an EventStore")
        self.event_store = event_store

    def timeline(
        self,
        *,
        event_types: Iterable[str] | None = None,
        cycle_id: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Return chronological event records, retaining causal and evidence links."""
        if limit is not None and (
            isinstance(limit, bool) or not isinstance(limit, int) or limit < 1
        ):
            raise ValueError("limit must be a positive integer")
        selected = None if event_types is None else set(event_types)
        if selected is not None and any(not isinstance(item, str) or not item for item in selected):
            raise ValueError("event_types must contain non-empty strings")
        if cycle_id is not None and (not isinstance(cycle_id, str) or not cycle_id.strip()):
            raise ValueError("cycle_id must be a non-empty string")

        events = self.event_store.all_events()
        records: list[dict[str, Any]] = []
        for event in events:
            if cycle_id is not None and event.cycle_id != cycle_id:
                continue
            if selected is not None and event.event_type not in selected:
                continue
            artifact = event.artifact
            records.append({
                "sequence": event.sequence,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "cycle_id": event.cycle_id,
                "created_at": event.created_at,
                "causation_id": event.causation_id,
                "event_hash": event.event_hash,
                "artifact": artifact.to_dict(),
                "artifact_id": artifact.id,
                "kind": artifact.kind,
                "producer": artifact.producer,
                "epistemic_status": artifact.epistemic_status,
                "confidence": artifact.confidence,
                "input_refs": list(artifact.input_refs),
                "source_refs": list(artifact.source_refs),
                "content": dict(artifact.data),
            })
        if limit is not None:
            records = records[-limit:]
        return records

    def describe(
        self,
        *,
        event_types: Iterable[str] | None = None,
        cycle_id: str | None = None,
    ) -> dict[str, Any]:
        """Build a compact factual account without inventing missing life history."""
        records = self.timeline(event_types=event_types, cycle_id=cycle_id)
        by_type = Counter(item["event_type"] for item in records)
        by_cycle = Counter(item["cycle_id"] for item in records)
        return {
            "record_count": len(records),
            "first_event": records[0] if records else None,
            "latest_event": records[-1] if records else None,
            "event_type_counts": dict(sorted(by_type.items())),
            "cycle_event_counts": dict(sorted(by_cycle.items())),
            "causal_links": [
                {"event_id": item["event_id"], "causation_id": item["causation_id"]}
                for item in records if item["causation_id"] is not None
            ],
            "timeline": records,
            "epistemic_note": (
                "This account reconstructs persisted operational records; "
                "it does not establish subjective experience or consciousness."
            ),
        }
