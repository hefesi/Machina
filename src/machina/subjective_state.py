"""D08.1: inspectable functional state for Self/world research.

"Subjective" here means agent-relative functional state only. It is not a
claim about phenomenal experience or consciousness.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidence:
    value: Any
    source: str
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("evidence source must be non-empty")
        if isinstance(self.confidence, bool) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass
class FunctionalSubjectiveState:
    """Structured, auditable snapshot of an agent-relative functional state."""

    world: dict[str, Evidence] = field(default_factory=dict)
    self_model: dict[str, Evidence] = field(default_factory=dict)
    memories: list[dict[str, Any]] = field(default_factory=list)
    goals: dict[str, float] = field(default_factory=dict)
    priorities: dict[str, float] = field(default_factory=dict)
    unknowns: set[str] = field(default_factory=set)
    version: int = 1

    def __post_init__(self) -> None:
        if self.version < 1:
            raise ValueError("version must be positive")
        for name, score in (*self.goals.items(), *self.priorities.items()):
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
                raise ValueError(f"score for {name!r} must be between 0 and 1")

    def set_world_fact(self, key: str, value: Any, source: str, confidence: float = 1.0) -> None:
        self.world[key] = Evidence(value, source, confidence)
        self.unknowns.discard(key)

    def set_self_fact(self, key: str, value: Any, source: str, confidence: float = 1.0) -> None:
        self.self_model[key] = Evidence(value, source, confidence)
        self.unknowns.discard(f"self:{key}")

    def mark_unknown(self, key: str, *, about_self: bool = False) -> None:
        self.unknowns.add(f"self:{key}" if about_self else key)

    def add_memory(self, event: str, *, source: str, importance: float = 0.5) -> None:
        if not event.strip() or not source.strip():
            raise ValueError("event and source must be non-empty")
        if isinstance(importance, bool) or not isinstance(importance, (int, float)) or not 0 <= importance <= 1:
            raise ValueError("importance must be between 0 and 1")
        self.memories.append({
            "event": event,
            "source": source,
            "importance": float(importance),
            "state_version": self.version,
        })

    def snapshot(self) -> dict[str, Any]:
        def evidence_map(items: dict[str, Evidence]) -> dict[str, dict[str, Any]]:
            return {
                key: {"value": item.value, "source": item.source, "confidence": item.confidence}
                for key, item in sorted(items.items())
            }
        return {
            "version": self.version,
            "world": evidence_map(self.world),
            "self_model": evidence_map(self.self_model),
            "memories": list(self.memories),
            "goals": dict(sorted(self.goals.items())),
            "priorities": dict(sorted(self.priorities.items())),
            "unknowns": sorted(self.unknowns),
        }
