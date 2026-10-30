"""Longitudinal analysis of operational SelfModel changes.

The analyzer compares explicit, evidence-bearing snapshots. It distinguishes
persistence across sampled checkpoints from recurrence and reversion; it does
not infer unobserved continuity between checkpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .self_model import SelfModel


@dataclass(frozen=True)
class SelfStateTransition:
    property_name: str
    initial_value: Any
    current_value: Any
    first_cycle: str
    last_cycle: str
    observations: int
    status: str
    evidence_refs: tuple[str, ...]


class SelfStateDynamicsAnalyzer:
    """Analyze the sampled history of one SelfModel property."""

    schema_version = 1

    @staticmethod
    def _snapshot(value: SelfModel | Mapping[str, Any]) -> dict[str, Any]:
        snapshot = value.snapshot() if isinstance(value, SelfModel) else dict(value)
        if snapshot.get("schema_version") != SelfModel.schema_version:
            raise ValueError("unsupported SelfModel snapshot")
        if not isinstance(snapshot.get("beliefs"), Mapping):
            raise ValueError("snapshot beliefs must be a mapping")
        return snapshot

    def analyze(
        self,
        history: Sequence[SelfModel | Mapping[str, Any]],
        property_name: str,
    ) -> SelfStateTransition:
        if isinstance(history, (str, bytes)) or not isinstance(history, Sequence) or len(history) < 2:
            raise ValueError("history must contain at least two SelfModel snapshots")
        if not isinstance(property_name, str) or not property_name.strip():
            raise ValueError("property_name must be non-empty")
        snapshots = [self._snapshot(item) for item in history]
        samples: list[tuple[str, Any, str]] = []
        for snapshot in snapshots:
            cycle = snapshot.get("cycle_id")
            belief = snapshot["beliefs"].get(property_name)
            if not isinstance(cycle, str) or not cycle.strip():
                raise ValueError("each snapshot must have a cycle_id")
            if not isinstance(belief, Mapping):
                continue
            if belief.get("status") != "observed":
                continue
            evidence = belief.get("evidence_ref")
            if not isinstance(evidence, str) or not evidence.strip():
                continue
            samples.append((cycle, belief.get("value"), evidence))
        if len(samples) < 2:
            raise ValueError("at least two evidence-backed observed samples are required")
        cycles = [item[0] for item in samples]
        if len(set(cycles)) != len(cycles):
            raise ValueError("sample cycle_ids must be unique")
        initial = samples[0][1]
        current = samples[-1][1]
        values = [item[1] for item in samples]
        seen_values: list[Any] = []
        for value in values:
            if value not in seen_values:
                seen_values.append(value)
        if current == initial:
            status = "reverted" if len(seen_values) > 1 else "stable"
        elif values.count(current) > 1:
            status = "recurrent"
        elif all(value == current for value in values[1:]):
            status = "persistent_since_change"
        else:
            status = "changed"
        return SelfStateTransition(
            property_name=property_name,
            initial_value=initial,
            current_value=current,
            first_cycle=cycles[0],
            last_cycle=cycles[-1],
            observations=len(samples),
            status=status,
            evidence_refs=tuple(item[2] for item in samples),
        )

    def analyze_all(
        self,
        history: Sequence[SelfModel | Mapping[str, Any]],
    ) -> tuple[SelfStateTransition, ...]:
        if isinstance(history, (str, bytes)) or not isinstance(history, Sequence) or len(history) < 2:
            raise ValueError("history must contain at least two SelfModel snapshots")
        snapshots = [self._snapshot(item) for item in history]
        properties = sorted(set.intersection(*[
            {key for key, belief in snapshot["beliefs"].items()
             if isinstance(belief, Mapping) and belief.get("status") == "observed"}
            for snapshot in snapshots
        ]))
        results = []
        for property_name in properties:
            try:
                results.append(self.analyze(snapshots, property_name))
            except ValueError:
                continue
        return tuple(results)
