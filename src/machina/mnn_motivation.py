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


class MotivationSystem:
    """Deterministic homeostatic drive ledger with explicit outcome updates."""

    SNAPSHOT_SCHEMA = 1

    def __init__(self, drives: list[MotivationalDrive] | None = None) -> None:
        self.drives: dict[str, MotivationalDrive] = {}
        self.timestep = 0
        for drive in drives or []:
            self.add_drive(drive)

    def add_drive(self, drive: MotivationalDrive) -> None:
        if not isinstance(drive, MotivationalDrive):
            raise ValueError("drive must be a MotivationalDrive")
        if drive.name in self.drives:
            raise ValueError(f"duplicate drive: {drive.name}")
        self.drives[drive.name] = drive

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
        return {name: drive.urgency for name, drive in self.drives.items()}

    def ranked_drives(self) -> list[tuple[str, float]]:
        """Return drives by descending urgency, with stable name-based tie breaks."""
        return sorted(
            ((name, drive.urgency) for name, drive in self.drives.items()),
            key=lambda item: (-item[1], item[0]),
        )

    @property
    def chemical_pressure(self) -> float:
        """Mean urgency presented as a bounded internal signal to neuromodulation."""
        if not self.drives:
            return 0.0
        return sum(drive.urgency for drive in self.drives.values()) / len(self.drives)

    def autonomy_adjustments(self, *, gain: float = 0.3) -> dict[str, float]:
        """Translate drive urgency into bounded per-drive goal-selection feedback.

        Centering at 0.5 makes neutral urgency produce no adjustment. The
        default gain maps [0, 1] to [-0.15, +0.15], matching AutonomyController's
        feedback clamp. This changes ranking only; it does not create goals.
        """
        gain = _bounded("gain", gain)
        if gain > 0.3:
            raise ValueError("gain must not exceed 0.3")
        return {
            name: (drive.urgency - 0.5) * gain
            for name, drive in self.drives.items()
        }

    def snapshot(self) -> dict[str, object]:
        return {
            "schema_version": self.SNAPSHOT_SCHEMA,
            "timestep": self.timestep,
            "drives": [drive.snapshot() for drive in self.drives.values()],
        }

    @classmethod
    def from_snapshot(cls, data: Mapping[str, object]) -> "MotivationSystem":
        if data.get("schema_version") != cls.SNAPSHOT_SCHEMA:
            raise ValueError("unsupported motivation snapshot schema")
        timestep = data.get("timestep")
        if isinstance(timestep, bool) or not isinstance(timestep, int) or timestep < 0:
            raise ValueError("motivation timestep must be a non-negative integer")
        raw_drives = data.get("drives")
        if not isinstance(raw_drives, list):
            raise ValueError("motivation drives must be a list")
        drives = [MotivationalDrive(**item) for item in raw_drives]
        system = cls(drives)
        system.timestep = timestep
        return system
