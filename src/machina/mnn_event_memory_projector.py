"""Replayable projection of the append-only EventStore into episodic memory."""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Iterable
from .event_store import EventStore, StoredEvent
from .fragment_memory import FragmentMemory

@dataclass(frozen=True, slots=True)
class MNNEventProjectionResult:
    scanned_count: int
    projected_count: int
    already_projected_count: int
    last_sequence: int

class MNNEventMemoryProjector:
    """Project immutable events into a rebuildable FragmentMemory read model."""
    def __init__(self, event_store: EventStore, memory: FragmentMemory) -> None:
        if not isinstance(event_store, EventStore):
            raise TypeError("event_store must be an EventStore")
        if not isinstance(memory, FragmentMemory):
            raise TypeError("memory must be a FragmentMemory")
        self.event_store = event_store
        self.memory = memory

    def project(self, *, after_sequence: int = 0, limit: int | None = None, event_types: Iterable[str] | None = None) -> MNNEventProjectionResult:
        """Replay events after a cursor. Persist last_sequence only after success."""
        if isinstance(after_sequence, bool) or not isinstance(after_sequence, int) or after_sequence < 0:
            raise ValueError("after_sequence must be a non-negative integer")
        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 1):
            raise ValueError("limit must be a positive integer or None")
        allowed = None
        if event_types is not None:
            values = list(event_types)
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError("event_types must contain non-empty strings")
            allowed = {item.strip() for item in values}
        events = [e for e in self.event_store.all_events() if e.sequence > after_sequence]
        if limit is not None:
            events = events[:limit]
        projected = 0
        already = 0
        last_sequence = after_sequence
        for event in events:
            last_sequence = event.sequence
            if allowed is not None and event.event_type not in allowed:
                continue
            if self._project_one(event):
                projected += 1
            else:
                already += 1
        return MNNEventProjectionResult(len(events), projected, already, last_sequence)

    def _project_one(self, event: StoredEvent) -> bool:
        artifact = event.artifact
        fragment_id = "event_" + event.event_id
        content = json.dumps(artifact.to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        metadata = {
            "projection": "event_store_v1", "event_id": event.event_id,
            "sequence": event.sequence, "cycle_id": event.cycle_id,
            "event_type": event.event_type, "event_hash": event.event_hash,
            "causation_id": event.causation_id, "artifact_id": artifact.id,
            "artifact_kind": artifact.kind, "epistemic_status": artifact.epistemic_status,
            "input_refs": list(artifact.input_refs), "source_refs": list(artifact.source_refs),
            "event_created_at": event.created_at,
        }
        source_uri = "eventstore://" + event.event_id
        try:
            existing = self.memory.get(fragment_id, record_access=False)
        except KeyError:
            self.memory.add(content, kind="episodic_event", source_uri=source_uri,
                importance=0.5, confidence=0.5 if artifact.confidence is None else artifact.confidence,
                tags=("event", event.event_type, artifact.kind, artifact.epistemic_status),
                metadata=metadata, fragment_id=fragment_id)
            return True
        expected_tags = ("event", event.event_type, artifact.kind, artifact.epistemic_status)
        expected_confidence = 0.5 if artifact.confidence is None else artifact.confidence
        if (existing.content != content or existing.kind != "episodic_event" or
            existing.source_uri != source_uri or existing.importance != 0.5 or
            existing.confidence != expected_confidence or existing.tags != expected_tags or
            existing.metadata != metadata):
            raise ValueError("projected memory conflicts with source event " + event.event_id)
        return False
