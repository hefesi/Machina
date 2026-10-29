"""Bounded, deterministic structural growth from co-activation.

The MNN substrate exposes explicit topology edits. This module adds a small
policy that chooses which directed edges to grow from the current unit states,
without claiming that co-activation is a complete model of structural
plasticity or autonomous development.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Iterable, Mapping

from .mnn import Connection, MNN


def _non_negative_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _positive_number(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite and positive")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be finite and positive") from error
    if not math.isfinite(number) or number <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return number


def _non_negative_number(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite and non-negative")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be finite and non-negative") from error
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return number


def _unit_set(value: Iterable[str] | None, name: str) -> frozenset[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        raise ValueError(f"{name} must be an iterable of unit IDs, not a string")
    try:
        units = frozenset(value)
    except TypeError as error:
        raise ValueError(f"{name} must be an iterable of unit IDs") from error
    if any(not isinstance(unit, str) or not unit for unit in units):
        raise ValueError(f"{name} must contain non-empty unit IDs")
    return units


@dataclass(frozen=True)
class GrownConnection:
    """An edge created by a growth policy, with the score that selected it."""

    connection: Connection
    score: float


class ActivityGrowthPolicy:
    """Grow a bounded number of edges between co-active units.

    Candidates are evaluated in deterministic order: highest absolute
    co-activation first, then source ID, then target ID. Existing directed
    pairs, self-connections, silent units, and degree/connection limits are
    excluded. The policy never modifies an existing edge's weight.
    """

    def __init__(
        self,
        *,
        max_new_connections: int = 1,
        initial_weight: float = 0.1,
        min_activity: float = 0.1,
        max_connections: int | None = None,
        max_out_degree: int | None = None,
        max_in_degree: int | None = None,
        allowed_sources: Iterable[str] | None = None,
        allowed_targets: Iterable[str] | None = None,
    ) -> None:
        self.max_new_connections = _non_negative_int(
            max_new_connections, "max_new_connections"
        )
        self.initial_weight = _positive_number(initial_weight, "initial_weight")
        self.min_activity = _non_negative_number(min_activity, "min_activity")
        self.max_connections = (
            None
            if max_connections is None
            else _non_negative_int(max_connections, "max_connections")
        )
        self.max_out_degree = (
            None
            if max_out_degree is None
            else _non_negative_int(max_out_degree, "max_out_degree")
        )
        self.max_in_degree = (
            None
            if max_in_degree is None
            else _non_negative_int(max_in_degree, "max_in_degree")
        )
        self.allowed_sources = _unit_set(allowed_sources, "allowed_sources")
        self.allowed_targets = _unit_set(allowed_targets, "allowed_targets")

    def grow(
        self,
        network: MNN,
        *,
        activity: Mapping[str, float] | None = None,
    ) -> list[GrownConnection]:
        """Grow edges and return them in the order they were added."""
        if not isinstance(network, MNN):
            raise ValueError("network must be an MNN instance")
        states = self._activity(network, activity)
        if self.max_new_connections == 0:
            return []
        if (
            self.max_connections is not None
            and len(network.connections) >= self.max_connections
        ):
            return []

        existing_pairs = {
            (edge.source, edge.target) for edge in network.connections.values()
        }
        out_degree = {
            unit_id: sum(1 for edge in network.connections.values() if edge.source == unit_id)
            for unit_id in network.units
        }
        in_degree = {
            unit_id: sum(1 for edge in network.connections.values() if edge.target == unit_id)
            for unit_id in network.units
        }

        candidates: list[tuple[float, str, str]] = []
        for source in sorted(states):
            if (
                self.allowed_sources is not None
                and source not in self.allowed_sources
            ):
                continue
            pre = states[source]
            if abs(pre) < self.min_activity:
                continue
            for target in sorted(states):
                if source == target:
                    continue
                if (
                    self.allowed_targets is not None
                    and target not in self.allowed_targets
                ):
                    continue
                if (source, target) in existing_pairs:
                    continue
                post = states[target]
                if abs(post) < self.min_activity:
                    continue
                score = abs(pre * post)
                if score <= 0:
                    continue
                candidates.append((score, source, target))

        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        grown: list[GrownConnection] = []
        for score, source, target in candidates:
            if len(grown) >= self.max_new_connections:
                break
            if (
                self.max_connections is not None
                and len(network.connections) >= self.max_connections
            ):
                break
            if (
                self.max_out_degree is not None
                and out_degree[source] >= self.max_out_degree
            ):
                continue
            if (
                self.max_in_degree is not None
                and in_degree[target] >= self.max_in_degree
            ):
                continue
            connection_id = self._connection_id(network, source, target)
            edge = network.grow_connection(
                connection_id,
                source,
                target,
                weight=self.initial_weight,
            )
            existing_pairs.add((source, target))
            out_degree[source] += 1
            in_degree[target] += 1
            grown.append(GrownConnection(connection=edge, score=score))
        return grown

    def _activity(
        self,
        network: MNN,
        activity: Mapping[str, float] | None,
    ) -> dict[str, float]:
        if activity is None:
            return {unit_id: unit.state for unit_id, unit in network.units.items()}
        if not isinstance(activity, Mapping):
            raise ValueError("activity must be a mapping")
        unknown = set(activity) - set(network.units)
        if unknown:
            labels = sorted(repr(unit_id) for unit_id in unknown)
            raise ValueError(f"activity references unknown units: {labels}")
        states = {unit_id: unit.state for unit_id, unit in network.units.items()}
        for unit_id, value in activity.items():
            if isinstance(value, bool):
                raise ValueError(f"activity for {unit_id!r} must be finite")
            try:
                number = float(value)
            except (TypeError, ValueError) as error:
                raise ValueError(f"activity for {unit_id!r} must be finite") from error
            if not math.isfinite(number):
                raise ValueError(f"activity for {unit_id!r} must be finite")
            states[unit_id] = number
        return states

    @staticmethod
    def _connection_id(network: MNN, source: str, target: str) -> str:
        base = f"grown:{source}->{target}"
        candidate = base
        suffix = 2
        while candidate in network.connections:
            candidate = f"{base}#{suffix}"
            suffix += 1
        return candidate
