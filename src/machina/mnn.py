"""Small, dependency-free executable substrate for the Machina Neural Network (MNN).

This is an experimental graph-based neural substrate, not an AGI claim. A step
uses synchronous state updates: every unit reads the previous timestep, then
all states are committed together. Plasticity is explicit and bounded.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


@dataclass
class Unit:
    """A computational unit with persistent activation state and bias."""
    id: str
    bias: float = 0.0
    state: float = 0.0
    activation: str = "tanh"

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("unit id cannot be empty")
        self.bias = _finite(self.bias, "bias")
        self.state = _finite(self.state, "state")
        if self.activation not in {"identity", "tanh", "sigmoid"}:
            raise ValueError("activation must be identity, tanh, or sigmoid")

    def activate(self, value: float) -> float:
        value = _finite(value, "activation input")
        if self.activation == "identity":
            return value
        if self.activation == "tanh":
            return math.tanh(value)
        # Stable sigmoid avoids overflow for large negative values.
        if value >= 0:
            z = math.exp(-value)
            return 1.0 / (1.0 + z)
        z = math.exp(value)
        return z / (1.0 + z)


@dataclass
class Connection:
    """Directed weighted edge; disabled edges do not transmit or learn."""
    id: str
    source: str
    target: str
    weight: float = 1.0
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.id or not self.source or not self.target:
            raise ValueError("connection id, source, and target are required")
        self.weight = _finite(self.weight, "weight")


class MNN:
    """Minimal stateful neural graph with explicit Hebbian plasticity.

    Inputs are clamped as unit states for the current step. All non-input units
    update synchronously from the previous state snapshot, so recurrent graphs
    are deterministic and do not depend on connection insertion order.
    """
    def __init__(self, *, weight_limit: float = 5.0) -> None:
        self.weight_limit = _finite(weight_limit, "weight_limit")
        if self.weight_limit <= 0:
            raise ValueError("weight_limit must be positive")
        self.units: dict[str, Unit] = {}
        self.connections: dict[str, Connection] = {}
        self.timestep = 0

    def add_unit(self, unit: Unit) -> None:
        if unit.id in self.units:
            raise ValueError(f"duplicate unit id: {unit.id}")
        self.units[unit.id] = unit

    def add_connection(self, connection: Connection) -> None:
        if connection.id in self.connections:
            raise ValueError(f"duplicate connection id: {connection.id}")
        if connection.source not in self.units or connection.target not in self.units:
            raise ValueError("connection endpoints must exist before adding an edge")
        self.connections[connection.id] = connection
        connection.weight = max(-self.weight_limit, min(self.weight_limit, connection.weight))

    def step(self, inputs: Mapping[str, float] | None = None) -> dict[str, float]:
        inputs = inputs or {}
        unknown = set(inputs) - self.units.keys()
        if unknown:
            raise ValueError(f"unknown input units: {sorted(unknown)}")
        input_values = {key: _finite(value, f"input {key}") for key, value in inputs.items()}
        previous = {key: unit.state for key, unit in self.units.items()}
        totals = {key: unit.bias for key, unit in self.units.items()}
        for edge in self.connections.values():
            if edge.enabled:
                totals[edge.target] += previous[edge.source] * edge.weight
        next_states = dict(previous)
        for key, value in input_values.items():
            next_states[key] = value
        for key, unit in self.units.items():
            if key not in input_values:
                next_states[key] = unit.activate(totals[key])
        for key, value in next_states.items():
            self.units[key].state = value
        self.timestep += 1
        return dict(next_states)

    def apply_hebbian(self, *, learning_rate: float, reward: float = 1.0) -> dict[str, float]:
        """Apply bounded reward-modulated Hebbian updates: Δw = η·r·pre·post."""
        rate = _finite(learning_rate, "learning_rate")
        reward_value = _finite(reward, "reward")
        if rate < 0:
            raise ValueError("learning_rate cannot be negative")
        changes: dict[str, float] = {}
        for edge in self.connections.values():
            if not edge.enabled:
                continue
            pre = self.units[edge.source].state
            post = self.units[edge.target].state
            proposed = edge.weight + rate * reward_value * pre * post
            updated = max(-self.weight_limit, min(self.weight_limit, proposed))
            changes[edge.id] = updated - edge.weight
            edge.weight = updated
        return changes

    def reset_states(self, value: float = 0.0) -> None:
        value = _finite(value, "value")
        for unit in self.units.values():
            unit.state = value
        self.timestep = 0

    def snapshot(self) -> dict:
        """Return JSON-compatible state for persistence or reproducible tests."""
        return {
            "schema_version": 1,
            "timestep": self.timestep,
            "weight_limit": self.weight_limit,
            "units": [
                {"id": u.id, "bias": u.bias, "state": u.state, "activation": u.activation}
                for u in self.units.values()
            ],
            "connections": [
                {"id": e.id, "source": e.source, "target": e.target,
                 "weight": e.weight, "enabled": e.enabled}
                for e in self.connections.values()
            ],
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNN":
        if data.get("schema_version") != 1:
            raise ValueError("unsupported MNN snapshot schema")
        network = cls(weight_limit=data["weight_limit"])
        for item in data["units"]:
            network.add_unit(Unit(**item))
        for item in data["connections"]:
            network.add_connection(Connection(**item))
        network.timestep = int(data["timestep"])
        if network.timestep < 0:
            raise ValueError("timestep cannot be negative")
        return network
