"""Versioned, auditable internal state assembled during a cognitive cycle."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping


INTERNAL_STATE_SCHEMA_VERSION = "machina.internal_state.v1"


@dataclass(frozen=True, slots=True)
class InternalStateSnapshot:
    """A cycle-local working representation, not a claim of subjective experience."""

    cycle_id: str
    observation_ref: str
    modality: str
    source_ref: str
    perception_confidence: float
    active_goal_ref: str
    retrieved_memory_refs: tuple[str, ...] = ()
    cognitive_result_ref: str | None = None
    understanding: Any = None
    uncertainties: tuple[Any, ...] = ()
    mnn_signal: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = INTERNAL_STATE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        for name in ("cycle_id", "observation_ref", "modality", "source_ref", "active_goal_ref"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be a non-empty string")
        if isinstance(self.perception_confidence, bool) or not isinstance(self.perception_confidence, (int, float)):
            raise ValueError("perception_confidence must be between 0 and 1")
        if not 0.0 <= self.perception_confidence <= 1.0:
            raise ValueError("perception_confidence must be between 0 and 1")
        if any(not isinstance(item, str) or not item for item in self.retrieved_memory_refs):
            raise ValueError("retrieved_memory_refs must contain non-empty strings")
        if not isinstance(self.mnn_signal, Mapping):
            raise ValueError("mnn_signal must be a mapping")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible snapshot for durable workspace storage."""
        result = asdict(self)
        result["retrieved_memory_refs"] = list(self.retrieved_memory_refs)
        result["uncertainties"] = list(self.uncertainties)
        result["mnn_signal"] = dict(self.mnn_signal)
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "InternalStateSnapshot":
        """Restore a snapshot while rejecting unknown schema versions."""
        if data.get("schema_version") != INTERNAL_STATE_SCHEMA_VERSION:
            raise ValueError("unsupported internal state schema version")
        values = dict(data)
        values["retrieved_memory_refs"] = tuple(values.get("retrieved_memory_refs", ()))
        values["uncertainties"] = tuple(values.get("uncertainties", ()))
        return cls(**values)
