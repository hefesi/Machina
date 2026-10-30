"""Lexical recall over the replayable EventStore autobiographical projection.

The EventStore remains authoritative. This service only retrieves validated
episodic fragments and exposes their original event provenance.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from .fragment_memory import FragmentMemory, MemoryFragment


@dataclass(frozen=True, slots=True)
class MNNAutobiographicalEpisode:
    """One recalled event with its immutable source identifiers."""

    fragment_id: str
    event_id: str
    sequence: int
    cycle_id: str
    event_type: str
    event_hash: str
    causation_id: str | None
    artifact_id: str
    artifact_kind: str
    epistemic_status: str
    artifact: Mapping[str, Any]


class MNNAutobiographicalRecall:
    """Retrieve prior EventStore events using FragmentMemory's lexical baseline.

    Retrieval is intentionally not semantic understanding. It does not infer
    causality, success, or usefulness from event proximity or reward values.
    """

    def __init__(self, memory: FragmentMemory) -> None:
        if not isinstance(memory, FragmentMemory):
            raise TypeError("memory must be a FragmentMemory")
        self.memory = memory

    def recall(
        self,
        query: str,
        *,
        limit: int = 5,
        context: str | None = None,
    ) -> tuple[MNNAutobiographicalEpisode, ...]:
        """Return the best lexical matches among episodic EventStore projections."""
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        fragments = self.memory.recall(
            query, limit=limit, include_related=True, context=context,
            kinds=("episodic_event",),
        )
        return tuple(self._episode(fragment) for fragment in fragments)

    @staticmethod
    def _episode(fragment: MemoryFragment) -> MNNAutobiographicalEpisode:
        metadata = dict(fragment.metadata)
        if metadata.get("projection") != "event_store_v1":
            raise ValueError("episodic fragment has an unknown projection version")
        try:
            artifact = json.loads(fragment.content)
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("episodic fragment contains invalid artifact JSON") from error
        if not isinstance(artifact, dict):
            raise ValueError("episodic fragment artifact must be a JSON object")
        required = (
            "event_id", "sequence", "cycle_id", "event_type", "event_hash",
            "artifact_id", "artifact_kind", "epistemic_status",
        )
        if any(key not in metadata for key in required):
            raise ValueError("episodic fragment is missing event provenance")
        if artifact.get("id") != metadata["artifact_id"]:
            raise ValueError("episodic fragment artifact ID conflicts with provenance")
        return MNNAutobiographicalEpisode(
            fragment_id=fragment.id,
            event_id=str(metadata["event_id"]),
            sequence=int(metadata["sequence"]),
            cycle_id=str(metadata["cycle_id"]),
            event_type=str(metadata["event_type"]),
            event_hash=str(metadata["event_hash"]),
            causation_id=metadata.get("causation_id"),
            artifact_id=str(metadata["artifact_id"]),
            artifact_kind=str(metadata["artifact_kind"]),
            epistemic_status=str(metadata["epistemic_status"]),
            artifact=artifact,
        )
