"""Activity-dependent short-term synaptic dynamics for the MNN.

The model tracks per-connection utilization (facilitation) and available
resources (depression/recovery). It is an explicit phenomenological model,
not a biochemical simulation.
"""
from __future__ import annotations

import math
from typing import Mapping

from .mnn import MNN


def _bounded(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be within [0, 1]")
    return float(value)


class MNNShortTermPlasticity:
    """Track fast facilitation and depression without permanently changing weights.

    For each edge, utilization relaxes toward baseline U and resources recover
    toward 1. Source activity in [0, 1] transiently consumes resources. The
    returned gain scales transmission for this step only; long-term weights
    remain owned by MNN and its learning rules.
    """

    schema_version = 1

    def __init__(
        self,
        network: MNN,
        *,
        baseline_utilization: float = 0.25,
        facilitation_rate: float = 0.2,
        recovery_rate: float = 0.1,
    ) -> None:
        if not isinstance(network, MNN):
            raise ValueError("network must be an MNN")
        self.baseline_utilization = _bounded(baseline_utilization, "baseline_utilization")
        if self.baseline_utilization == 0.0:
            raise ValueError("baseline_utilization must be greater than zero")
        self.facilitation_rate = _bounded(facilitation_rate, "facilitation_rate")
        self.recovery_rate = _bounded(recovery_rate, "recovery_rate")
        self.utilization = {edge_id: self.baseline_utilization for edge_id in network.connections}
        self.resources = {edge_id: 1.0 for edge_id in network.connections}

    def gains(self, network: MNN) -> dict[str, float]:
        """Advance fast synaptic state and return per-edge transmission gains."""
        if not isinstance(network, MNN):
            raise ValueError("network must be an MNN")
        live = set(network.connections)
        if not set(self.utilization).issubset(live) or set(self.utilization) != set(self.resources):
            raise ValueError("network topology changed; explicitly reconcile plasticity state")
        result: dict[str, float] = {}
        for edge_id, edge in network.connections.items():
            if not edge.enabled:
                result[edge_id] = 0.0
                continue
            activity = min(1.0, abs(network.units[edge.source].state))
            u = self.utilization[edge_id]
            x = self.resources[edge_id]
            u += self.facilitation_rate * (self.baseline_utilization - u)
            x += self.recovery_rate * (1.0 - x)
            if activity > 0.0:
                u = u + self.facilitation_rate * activity * (1.0 - u)
                released_fraction = min(1.0, u * activity)
                x = max(0.0, x * (1.0 - released_fraction))
            else:
                released_fraction = self.baseline_utilization
            self.utilization[edge_id] = min(1.0, max(0.0, u))
            self.resources[edge_id] = min(1.0, max(0.0, x))
            result[edge_id] = max(0.0, (released_fraction * x) / self.baseline_utilization)
        return result

    def step(self, network: MNN, inputs: Mapping[str, float] | None = None) -> dict[str, float]:
        """Advance short-term synaptic state and then one MNN timestep."""
        return network.step(inputs, connection_gains=self.gains(network))

    def reset(self, network: MNN) -> None:
        """Reset fast state to baseline without changing long-term weights."""
        self.utilization = {edge_id: self.baseline_utilization for edge_id in network.connections}
        self.resources = {edge_id: 1.0 for edge_id in network.connections}

    def snapshot(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "baseline_utilization": self.baseline_utilization,
            "facilitation_rate": self.facilitation_rate,
            "recovery_rate": self.recovery_rate,
            "utilization": dict(sorted(self.utilization.items())),
            "resources": dict(sorted(self.resources.items())),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping, network: MNN) -> "MNNShortTermPlasticity":
        if not isinstance(data, Mapping) or data.get("schema_version") != cls.schema_version:
            raise ValueError("unsupported short-term-plasticity snapshot schema")
        result = cls(
            network,
            baseline_utilization=data["baseline_utilization"],
            facilitation_rate=data["facilitation_rate"],
            recovery_rate=data["recovery_rate"],
        )
        utilization, resources = data.get("utilization"), data.get("resources")
        if not isinstance(utilization, Mapping) or not isinstance(resources, Mapping):
            raise ValueError("short-term state must contain utilization and resources mappings")
        expected = set(network.connections)
        if set(utilization) != expected or set(resources) != expected:
            raise ValueError("snapshot topology does not match network")
        result.utilization = {key: _bounded(value, f"utilization {key}") for key, value in utilization.items()}
        result.resources = {key: _bounded(value, f"resources {key}") for key, value in resources.items()}
        return result
