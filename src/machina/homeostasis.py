"""Persistent, evidence-grounded computational homeostasis.

Rules detect sustained deviations in observed operational telemetry and emit
bounded drive-adjustment proposals. They do not mutate the SelfModel, MNN,
motivation system, or execute actions.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Mapping

from .self_model import SelfModel


@dataclass(frozen=True)
class HomeostaticRule:
    """Explicit policy for one measured variable and its corrective drive."""

    metric_key: str
    drive: str
    lower: float
    upper: float
    below_adjustment: float
    above_adjustment: float

    def __post_init__(self) -> None:
        if not isinstance(self.metric_key, str) or not self.metric_key.strip():
            raise ValueError("metric_key must be a non-empty string")
        if not isinstance(self.drive, str) or not self.drive.strip():
            raise ValueError("drive must be a non-empty string")
        for name in ("lower", "upper"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and within [0, 1]")
        if self.lower >= self.upper:
            raise ValueError("lower must be less than upper")
        for name in ("below_adjustment", "above_adjustment"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not -0.3 <= value <= 0.3:
                raise ValueError(f"{name} must be finite and within [-0.3, 0.3]")


@dataclass(frozen=True)
class HomeostaticProposal:
    cycle_id: str
    adjustments: Mapping[str, float]
    deviations: Mapping[str, float]
    persistence: Mapping[str, int]
    evidence_refs: tuple[str, ...]
    rationale: tuple[str, ...]


class HomeostaticRegulator:
    """Detect sustained out-of-range observations and propose compensation."""

    schema_version = 1

    def __init__(
        self,
        self_model: SelfModel,
        rules: Mapping[str, HomeostaticRule],
        *,
        persistence_cycles: int = 3,
    ) -> None:
        if not isinstance(self_model, SelfModel):
            raise TypeError("self_model must be a SelfModel")
        if not isinstance(rules, Mapping) or not rules:
            raise ValueError("rules must be a non-empty mapping")
        if isinstance(persistence_cycles, bool) or not isinstance(persistence_cycles, int) or persistence_cycles < 1:
            raise ValueError("persistence_cycles must be a positive integer")
        normalized: dict[str, HomeostaticRule] = {}
        for name, rule in rules.items():
            if not isinstance(name, str) or not name.strip() or not isinstance(rule, HomeostaticRule):
                raise ValueError("rules must map non-empty names to HomeostaticRule values")
            normalized[name] = rule
        self.self_model = self_model
        self.rules = normalized
        self.persistence_cycles = persistence_cycles
        self._streaks: dict[str, dict[str, Any]] = {
            name: {"direction": None, "count": 0} for name in normalized
        }
        self._last_cycle_id: str | None = None

    def assess(self, *, cycle_id: str | None = None) -> HomeostaticProposal:
        """Assess exactly one new SelfModel cycle; duplicate cycles are rejected."""
        selected_cycle = cycle_id or self.self_model.cycle_id
        if not isinstance(selected_cycle, str) or not selected_cycle.strip():
            raise ValueError("SelfModel has no cycle; supply cycle_id")
        if selected_cycle == self._last_cycle_id:
            raise ValueError("cycle_id has already been assessed")
        beliefs = self.self_model.beliefs
        adjustments: dict[str, float] = {}
        deviations: dict[str, float] = {}
        evidence: set[str] = set()
        rationale: list[str] = []
        for name, rule in self.rules.items():
            belief = beliefs.get(rule.metric_key)
            if not belief or belief.get("status") != "observed":
                self._streaks[name] = {"direction": None, "count": 0}
                rationale.append(f"{name}: no current observed telemetry; streak reset")
                continue
            value = belief.get("value")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                self._streaks[name] = {"direction": None, "count": 0}
                rationale.append(f"{name}: non-numeric telemetry; streak reset")
                continue
            direction = "below" if value < rule.lower else "above" if value > rule.upper else None
            if direction is None:
                self._streaks[name] = {"direction": None, "count": 0}
                rationale.append(f"{name}: within configured range")
                continue
            previous = self._streaks[name]
            count = previous["count"] + 1 if previous["direction"] == direction else 1
            self._streaks[name] = {"direction": direction, "count": count}
            boundary = rule.lower if direction == "below" else rule.upper
            deviation = float(value) - boundary
            deviations[name] = deviation
            ref = belief.get("evidence_ref")
            if isinstance(ref, str) and ref:
                evidence.add(ref)
            if count >= self.persistence_cycles:
                amount = rule.below_adjustment if direction == "below" else rule.above_adjustment
                adjustments[rule.drive] = max(-0.3, min(0.3, amount))
            rationale.append(
                f"{name}: {direction} range by {abs(deviation):.6f}; "
                f"persistent cycles={count}/{self.persistence_cycles}; "
                f"drive={rule.drive}; proposal="
                f"{adjustments.get(rule.drive, 0.0):.6f}"
            )
        self._last_cycle_id = selected_cycle
        return HomeostaticProposal(
            cycle_id=selected_cycle,
            adjustments=adjustments,
            deviations=deviations,
            persistence={name: state["count"] for name, state in self._streaks.items()},
            evidence_refs=tuple(sorted(evidence)),
            rationale=tuple(rationale),
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "persistence_cycles": self.persistence_cycles,
            "rules": {name: asdict(rule) for name, rule in self.rules.items()},
            "streaks": {name: dict(state) for name, state in self._streaks.items()},
            "last_cycle_id": self._last_cycle_id,
        }

    @classmethod
    def from_snapshot(cls, self_model: SelfModel, data: Mapping[str, Any]) -> "HomeostaticRegulator":
        if not isinstance(data, Mapping) or data.get("schema_version") != cls.schema_version:
            raise ValueError("unsupported HomeostaticRegulator snapshot")
        raw_rules = data.get("rules")
        raw_streaks = data.get("streaks")
        if not isinstance(raw_rules, Mapping) or not isinstance(raw_streaks, Mapping):
            raise ValueError("snapshot rules and streaks must be mappings")
        rules = {name: HomeostaticRule(**rule) for name, rule in raw_rules.items()}
        regulator = cls(self_model, rules, persistence_cycles=data.get("persistence_cycles"))
        if set(raw_streaks) != set(rules):
            raise ValueError("snapshot streaks do not match rules")
        for name, state in raw_streaks.items():
            if not isinstance(state, Mapping) or state.get("direction") not in (None, "below", "above"):
                raise ValueError("invalid homeostatic streak")
            count = state.get("count")
            if isinstance(count, bool) or not isinstance(count, int) or not 0 <= count <= 1000000:
                raise ValueError("invalid homeostatic streak count")
            if (state.get("direction") is None) != (count == 0):
                raise ValueError("inconsistent homeostatic streak")
            regulator._streaks[name] = {"direction": state["direction"], "count": count}
        last = data.get("last_cycle_id")
        if last is not None and (not isinstance(last, str) or not last.strip()):
            raise ValueError("invalid last_cycle_id")
        regulator._last_cycle_id = last
        return regulator
