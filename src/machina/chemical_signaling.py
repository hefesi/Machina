"""MNN v0.10: bounded virtual chemical signaling for motivation experiments.

This is a computational control mechanism inspired by neuromodulation, not a
biochemical simulation and not a claim about feelings or consciousness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Mapping

CHEMICALS = ("dopamine", "acetylcholine", "noradrenaline", "serotonin")


def _finite_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _unit_interval(name: str, value: float) -> float:
    value = _finite_number(name, value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


@dataclass(frozen=True)
class ChemicalParameters:
    """Production and decay settings; concentrations are normalized to [0, 1]."""
    dopamine_decay: float = 0.18
    acetylcholine_decay: float = 0.22
    noradrenaline_decay: float = 0.25
    serotonin_decay: float = 0.08
    production_gain: float = 0.35

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            _unit_interval(name, value)


@dataclass
class ChemicalState:
    """Persistent virtual concentrations and prediction state."""
    dopamine: float = 0.0
    acetylcholine: float = 0.0
    noradrenaline: float = 0.0
    serotonin: float = 0.0
    expected_value: float = 0.0
    timestep: int = 0

    def __post_init__(self) -> None:
        for name in CHEMICALS:
            setattr(self, name, _unit_interval(name, getattr(self, name)))
        self.expected_value = _finite_number("expected_value", self.expected_value)
        if isinstance(self.timestep, bool) or not isinstance(self.timestep, int) or self.timestep < 0:
            raise ValueError("timestep must be a non-negative integer")

    def snapshot(self) -> dict[str, float | int]:
        return {name: getattr(self, name) for name in (*CHEMICALS, "expected_value", "timestep")}

    @classmethod
    def from_snapshot(cls, data: Mapping[str, object]) -> "ChemicalState":
        allowed = {*CHEMICALS, "expected_value", "timestep"}
        if set(data) - allowed:
            raise ValueError("snapshot contains unknown fields")
        return cls(**dict(data))  # type: ignore[arg-type]


@dataclass(frozen=True)
class ChemicalEvent:
    """Normalized event features emitted by a task/learning system."""
    reward: float = 0.0
    novelty: float = 0.0
    uncertainty: float = 0.0
    effort: float = 0.0
    progress: float = 0.0
    risk: float = 0.0
    motivational_pressure: float = 0.0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            _unit_interval(name, value)


@dataclass(frozen=True)
class ChemicalUpdate:
    prediction_error: float
    concentrations: Mapping[str, float]
    exploration_drive: float
    plasticity_gain: float
    attention_gain: float


class ChemicalSignaling:
    """Deterministic, bounded neuromodulator-inspired state machine.

    step receives normalized event features and advances one logical timestep.
    No wall-clock time, randomness, or external dependency is used.
    """

    def __init__(
        self,
        state: ChemicalState | None = None,
        parameters: ChemicalParameters | None = None,
        learning_rate: float = 0.2,
    ) -> None:
        self.state = state or ChemicalState()
        self.parameters = parameters or ChemicalParameters()
        self.learning_rate = _unit_interval("learning_rate", learning_rate)

    @staticmethod
    def _clamp(value: float) -> float:
        return min(1.0, max(0.0, value))

    def step(self, event: ChemicalEvent) -> ChemicalUpdate:
        s, p = self.state, self.parameters
        prediction_error = event.reward - s.expected_value
        s.expected_value += self.learning_rate * prediction_error

        gain = p.production_gain
        targets = {
            "dopamine": self._clamp(0.5 + 0.5 * prediction_error),
            "acetylcholine": self._clamp(0.55 * event.novelty + 0.25 * event.uncertainty + 0.20 * event.motivational_pressure),
            "noradrenaline": self._clamp(0.5 * event.uncertainty + 0.3 * event.risk + 0.2 * event.motivational_pressure),
            "serotonin": self._clamp(0.6 * (1.0 - event.risk) + 0.4 * event.progress),
        }
        decays = {
            "dopamine": p.dopamine_decay,
            "acetylcholine": p.acetylcholine_decay,
            "noradrenaline": p.noradrenaline_decay,
            "serotonin": p.serotonin_decay,
        }
        for name in CHEMICALS:
            old = getattr(s, name)
            new = old + gain * targets[name] * (1.0 - old) - decays[name] * old
            setattr(s, name, self._clamp(new))
        s.timestep += 1

        exploration = self._clamp(
            0.50 * s.acetylcholine + 0.35 * event.uncertainty
            + 0.15 * event.novelty + 0.20 * event.motivational_pressure - 0.25 * event.risk
        )
        plasticity = self._clamp(0.25 + 0.5 * abs(prediction_error) + 0.25 * s.acetylcholine)
        attention = self._clamp(0.4 + 0.4 * s.acetylcholine + 0.2 * s.noradrenaline)
        return ChemicalUpdate(
            prediction_error=prediction_error,
            concentrations={name: getattr(s, name) for name in CHEMICALS},
            exploration_drive=exploration,
            plasticity_gain=plasticity,
            attention_gain=attention,
        )

    def snapshot(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "state": self.state.snapshot(),
            "parameters": asdict(self.parameters),
            "learning_rate": self.learning_rate,
        }

    @classmethod
    def from_snapshot(cls, data: Mapping[str, object]) -> "ChemicalSignaling":
        if data.get("schema_version") != 1:
            raise ValueError("unsupported chemical-signaling snapshot schema")
        state_data, parameter_data = data.get("state"), data.get("parameters")
        if not isinstance(state_data, Mapping) or not isinstance(parameter_data, Mapping):
            raise ValueError("snapshot state and parameters must be mappings")
        return cls(
            state=ChemicalState.from_snapshot(state_data),
            parameters=ChemicalParameters(**dict(parameter_data)),  # type: ignore[arg-type]
            learning_rate=data.get("learning_rate", 0.2),  # type: ignore[arg-type]
        )
