"""Persistent, bounded internal-need dynamics for MNN experiments.

Drive values are explicit computational variables, not claims of biological
needs, emotions, or phenomenal experience.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Mapping


def _finite(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _bounded(name: str, value: float) -> float:
    value = _finite(name, value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be within [0, 1]")
    return value


@dataclass
class MotivationalDrive:
    """One persistent deficit variable with recovery and outcome sensitivity."""

    name: str
    level: float = 0.5
    setpoint: float = 0.5
    priority: float = 1.0
    recovery_rate: float = 0.02
    relief_gain: float = 0.25

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("drive name must be non-empty")
        for field in ("level", "setpoint", "priority", "recovery_rate", "relief_gain"):
            setattr(self, field, _bounded(field, getattr(self, field)))

    @property
    def urgency(self) -> float:
        """Priority-weighted current deficit, bounded to [0, 1]."""
        return min(1.0, max(0.0, self.level * self.priority))

    def advance(self, fulfillment: float = 0.0) -> float:
        """Recover toward setpoint, then reduce deficit by observed fulfillment."""
        amount = _bounded("fulfillment", fulfillment)
        self.level += self.recovery_rate * (self.setpoint - self.level)
        self.level = max(0.0, self.level - self.relief_gain * amount)
        self.level = min(1.0, max(0.0, self.level))
        return self.level

    def snapshot(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MotivationalConflict:
    """Directed-independent competition edge between two distinct drives."""

    first: str
    second: str
    strength: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.first, str) or not self.first.strip():
            raise ValueError("conflict first drive must be non-empty")
        if not isinstance(self.second, str) or not self.second.strip():
            raise ValueError("conflict second drive must be non-empty")
        if self.first == self.second:
            raise ValueError("a drive cannot conflict with itself")
        object.__setattr__(self, "strength", _bounded("conflict strength", self.strength))


@dataclass(frozen=True)
class MotivationalCooperation:
    """Symmetric positive coupling between two distinct motivational drives."""

    first: str
    second: str
    strength: float = 0.5

    def __post_init__(self) -> None:
        if not isinstance(self.first, str) or not self.first.strip():
            raise ValueError("cooperation first drive must be non-empty")
        if not isinstance(self.second, str) or not self.second.strip():
            raise ValueError("cooperation second drive must be non-empty")
        if self.first == self.second:
            raise ValueError("a drive cannot cooperate with itself")
        object.__setattr__(self, "strength", _bounded("cooperation strength", self.strength))


class MotivationSystem:
    """Deterministic drive ledger with explicit, bounded conflict arbitration."""

    SNAPSHOT_SCHEMA = 3

    def __init__(
        self,
        drives: list[MotivationalDrive] | None = None,
        conflicts: list[MotivationalConflict] | None = None,
        *,
        cooperations: list[MotivationalCooperation] | None = None,
        conflict_gain: float = 0.5,
        cooperation_gain: float = 0.25,
    ) -> None:
        self.drives: dict[str, MotivationalDrive] = {}
        self.conflicts: dict[tuple[str, str], MotivationalConflict] = {}
        self.conflict_gain = _bounded("conflict_gain", conflict_gain)
        self.timestep = 0
        for drive in drives or []:
            self.add_drive(drive)
        for conflict in conflicts or []:
            self.add_conflict(conflict)
        for cooperation in cooperations or []:
            self.add_cooperation(cooperation)

    def add_drive(self, drive: MotivationalDrive) -> None:
        if not isinstance(drive, MotivationalDrive):
            raise ValueError("drive must be a MotivationalDrive")
        if drive.name in self.drives:
            raise ValueError(f"duplicate drive: {drive.name}")
        self.drives[drive.name] = drive

    def add_conflict(self, conflict: MotivationalConflict) -> None:
        """Register one symmetric competition edge between existing drives."""
        if not isinstance(conflict, MotivationalConflict):
            raise ValueError("conflict must be a MotivationalConflict")
        if conflict.first not in self.drives or conflict.second not in self.drives:
            raise ValueError("conflict references an unknown motivational drive")
        key = tuple(sorted((conflict.first, conflict.second)))
        if key in self.conflicts:
            raise ValueError(f"duplicate motivational conflict: {key}")
        if key in self.cooperations:
            raise ValueError(f"drive pair already has a cooperation relation: {key}")
        self.conflicts[key] = conflict

    def add_cooperation(self, cooperation: MotivationalCooperation) -> None:
        """Register one symmetric positive coupling edge."""
        if not isinstance(cooperation, MotivationalCooperation):
            raise ValueError("cooperation must be a MotivationalCooperation")
        if cooperation.first not in self.drives or cooperation.second not in self.drives:
            raise ValueError("cooperation references an unknown motivational drive")
        key = tuple(sorted((cooperation.first, cooperation.second)))
        if key in self.cooperations:
            raise ValueError(f"duplicate motivational cooperation: {key}")
        if key in self.conflicts:
            raise ValueError(f"drive pair already has a conflict relation: {key}")
        self.cooperations[key] = cooperation

    def validate_fulfillment(
        self, fulfillment: Mapping[str, float] | None = None
    ) -> dict[str, float]:
        """Validate and normalize all fulfillment observations without mutation."""
        outcomes = dict(fulfillment or {})
        unknown = set(outcomes) - self.drives.keys()
        if unknown:
            raise ValueError(f"unknown motivational drives: {sorted(unknown)}")
        return {
            name: _bounded(f"fulfillment[{name}]", value)
            for name, value in outcomes.items()
        }

    def step(self, fulfillment: Mapping[str, float] | None = None) -> dict[str, float]:
        """Advance all drives once; omitted outcomes mean no fulfillment."""
        validated = self.validate_fulfillment(fulfillment)
        for name, drive in self.drives.items():
            drive.advance(validated.get(name, 0.0))
        self.timestep += 1
        return self.effective_urgencies()

    def effective_urgencies(self, *, gain: float | None = None) -> dict[str, float]:
        """Return urgency after symmetric, order-independent competition.

        Cooperative partners contribute a bounded positive boost first;
        competing partners then contribute bounded inhibition. The raw drive
        deficit is never overwritten.
        """
        selected_gain = self.conflict_gain if gain is None else _bounded("gain", gain)
        opponents: dict[str, list[tuple[float, float]]] = {
            name: [] for name in self.drives
        }
        for conflict in self.conflicts.values():
            first = self.drives[conflict.first].urgency
            second = self.drives[conflict.second].urgency
            if conflict.strength:
                opponents[conflict.first].append((conflict.strength, second))
                opponents[conflict.second].append((conflict.strength, first))

        partners: dict[str, list[tuple[float, float]]] = {
            name: [] for name in self.drives
        }
        for relation in self.cooperations.values():
            first = self.drives[relation.first].urgency
            second = self.drives[relation.second].urgency
            if relation.strength:
                partners[relation.first].append((relation.strength, second))
                partners[relation.second].append((relation.strength, first))

        result: dict[str, float] = {}
        for name, drive in self.drives.items():
            cooperative_links = partners[name]
            boost = 0.0
            if cooperative_links:
                total_weight = sum(weight for weight, _ in cooperative_links)
                partner_pressure = sum(weight * urgency for weight, urgency in cooperative_links) / total_weight
                boost = self.cooperation_gain * partner_pressure
            conflict_links = opponents[name]
            inhibition = 0.0
            if conflict_links:
                total_weight = sum(weight for weight, _ in conflict_links)
                competing_pressure = sum(weight * urgency for weight, urgency in conflict_links) / total_weight
                inhibition = selected_gain * competing_pressure
            result[name] = max(0.0, min(1.0, drive.urgency + boost - inhibition))
        return result

    def ranked_drives(self) -> list[tuple[str, float]]:
        """Rank conflict-adjusted urgency, with stable name-based tie breaks."""
        return sorted(
            self.effective_urgencies().items(),
            key=lambda item: (-item[1], item[0]),
        )

    @property
    def chemical_pressure(self) -> float:
        """Mean conflict-adjusted urgency for downstream virtual signaling."""
        effective = self.effective_urgencies()
        if not effective:
            return 0.0
        return sum(effective.values()) / len(effective)

    def autonomy_adjustments(self, *, gain: float = 0.3) -> dict[str, float]:
        """Translate arbitrated urgency into bounded goal-selection feedback."""
        gain = _bounded("gain", gain)
        if gain > 0.3:
            raise ValueError("gain must not exceed 0.3")
        return {
            name: (urgency - 0.5) * gain
            for name, urgency in self.effective_urgencies().items()
        }

    def snapshot(self) -> dict[str, object]:
        return {
            "schema_version": self.SNAPSHOT_SCHEMA,
            "timestep": self.timestep,
            "drives": [drive.snapshot() for drive in self.drives.values()],
            "conflicts": [
                {"first": item.first, "second": item.second, "strength": item.strength}
                for item in self.conflicts.values()
            ],
            "conflict_gain": self.conflict_gain,
            "cooperations": [
                {"first": item.first, "second": item.second, "strength": item.strength}
                for item in self.cooperations.values()
            ],
            "cooperation_gain": self.cooperation_gain,
        }

    @classmethod
    def from_snapshot(cls, data: Mapping[str, object]) -> "MotivationSystem":
        schema = data.get("schema_version")
        if schema not in (1, 2, cls.SNAPSHOT_SCHEMA):
            raise ValueError("unsupported motivation snapshot schema")
        timestep = data.get("timestep")
        if isinstance(timestep, bool) or not isinstance(timestep, int) or timestep < 0:
            raise ValueError("motivation timestep must be a non-negative integer")
        raw_drives = data.get("drives")
        if not isinstance(raw_drives, list):
            raise ValueError("motivation drives must be a list")
        drives = [MotivationalDrive(**item) for item in raw_drives]
        raw_conflicts = data.get("conflicts", [])
        if not isinstance(raw_conflicts, list):
            raise ValueError("motivation conflicts must be a list")
        conflicts = [MotivationalConflict(**item) for item in raw_conflicts]
        raw_cooperations = data.get("cooperations", [])
        if not isinstance(raw_cooperations, list):
            raise ValueError("motivation cooperations must be a list")
        cooperations = [MotivationalCooperation(**item) for item in raw_cooperations]
        system = cls(
            drives,
            conflicts,
            cooperations=cooperations,
            conflict_gain=data.get("conflict_gain", 0.5),
            cooperation_gain=data.get("cooperation_gain", 0.25),
        )
        system.timestep = timestep
        return system
