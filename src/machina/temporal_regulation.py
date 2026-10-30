"""Temporal smoothing for bounded self-regulation proposals."""
from __future__ import annotations

from dataclasses import replace
import math
from typing import Mapping

from .self_regulation import RegulationProposal


class TemporalRegulationFilter:
    """Smooth successive proposals to reduce oscillation in control signals.

    The filter changes only its own checkpointed state. It does not apply
    adjustments to motivation, goals, MNN weights, or external actions.
    """

    SNAPSHOT_SCHEMA = 1

    def __init__(self, *, alpha: float = 0.35, deadband: float = 0.005) -> None:
        self._validate_unit("alpha", alpha)
        self._validate_unit("deadband", deadband)
        if alpha <= 0:
            raise ValueError("alpha must be greater than zero")
        self.alpha = float(alpha)
        self.deadband = float(deadband)
        self._smoothed: dict[str, float] = {}
        self.timestep = 0

    @staticmethod
    def _validate_unit(name: str, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be finite and within [0, 1]")

    def filter(self, proposal: RegulationProposal) -> RegulationProposal:
        """Advance temporal smoothing and return a new proposal."""
        if not isinstance(proposal, RegulationProposal):
            raise TypeError("proposal must be a RegulationProposal")
        values: dict[str, float] = {}
        for drive, raw in proposal.adjustments.items():
            if not isinstance(drive, str) or not drive.strip():
                raise ValueError("proposal drive names must be non-empty")
            if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw) or abs(raw) > 0.3:
                raise ValueError("proposal adjustments must be finite and within [-0.3, 0.3]")
            previous = self._smoothed.get(drive, 0.0)
            current = previous + self.alpha * (float(raw) - previous)
            if abs(current) < self.deadband:
                current = 0.0
            values[drive] = current
        # Only commit after all values have passed validation.
        self._smoothed.update(values)
        self.timestep += 1
        rationale = proposal.rationale + (
            f"temporal_filter: alpha={self.alpha:.6f}, deadband={self.deadband:.6f}, "
            f"filter_timestep={self.timestep}",
        )
        return replace(proposal, adjustments=values, rationale=rationale)

    def snapshot(self) -> dict[str, object]:
        return {
            "schema_version": self.SNAPSHOT_SCHEMA,
            "alpha": self.alpha,
            "deadband": self.deadband,
            "timestep": self.timestep,
            "smoothed": dict(self._smoothed),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping[str, object]) -> "TemporalRegulationFilter":
        if not isinstance(data, Mapping) or data.get("schema_version") != cls.SNAPSHOT_SCHEMA:
            raise ValueError("unsupported temporal regulation snapshot schema")
        instance = cls(alpha=data.get("alpha"), deadband=data.get("deadband"))
        timestep = data.get("timestep")
        smoothed = data.get("smoothed")
        if isinstance(timestep, bool) or not isinstance(timestep, int) or timestep < 0:
            raise ValueError("filter timestep must be a non-negative integer")
        if not isinstance(smoothed, Mapping):
            raise ValueError("smoothed state must be a mapping")
        restored: dict[str, float] = {}
        for drive, value in smoothed.items():
            if not isinstance(drive, str) or not drive.strip():
                raise ValueError("smoothed drive names must be non-empty")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 0.3:
                raise ValueError("smoothed values must be finite and within [-0.3, 0.3]")
            restored[drive] = float(value)
        instance.timestep = timestep
        instance._smoothed = restored
        return instance
