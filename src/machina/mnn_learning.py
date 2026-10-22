"""Eligibility traces for delayed reward-modulated MNN learning.

This module complements immediate Hebbian plasticity with an explicit three-
factor rule: co-activity leaves a decaying eligibility trace, and a later reward
modulates that trace. It is a research baseline, not a biological model.
"""
from __future__ import annotations

import math
from typing import Mapping

from .mnn import MNN


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


class EligibilityTraceLearner:
    """Track connection co-activity and assign credit when reward arrives.

    Call record_activity after relevant network steps, then apply_reward when
    feedback arrives. The rule is e <- decay * e + pre * post, followed by
    weight <- clamp(weight + learning_rate * reward * e).

    Traces can be snapshotted separately from the MNN topology so callers can
    persist them alongside their own checkpoint or event journal.
    """

    schema_version = 1

    def __init__(
        self,
        network: MNN,
        *,
        learning_rate: float = 0.1,
        trace_decay: float = 0.8,
        trace_limit: float = 5.0,
    ) -> None:
        self.network = network
        self.learning_rate = _finite(learning_rate, "learning_rate")
        self.trace_decay = _finite(trace_decay, "trace_decay")
        self.trace_limit = _finite(trace_limit, "trace_limit")
        if self.learning_rate < 0:
            raise ValueError("learning_rate cannot be negative")
        if not 0.0 <= self.trace_decay <= 1.0:
            raise ValueError("trace_decay must be between 0 and 1")
        if self.trace_limit <= 0:
            raise ValueError("trace_limit must be positive")
        self.traces: dict[str, float] = {
            edge_id: 0.0 for edge_id in network.connections
        }

    def record_activity(self) -> dict[str, float]:
        """Accumulate bounded pre/post co-activity for enabled connections."""
        self._sync_connections()
        for edge_id, edge in self.network.connections.items():
            if not edge.enabled:
                self.traces[edge_id] = 0.0
                continue
            pre = self.network.units[edge.source].state
            post = self.network.units[edge.target].state
            value = self.trace_decay * self.traces[edge_id] + pre * post
            self.traces[edge_id] = max(-self.trace_limit, min(self.trace_limit, value))
        return dict(self.traces)

    def apply_reward(self, reward: float, *, clear: bool = False) -> dict[str, float]:
        """Apply a delayed reward to accumulated traces, respecting weight limits."""
        reward_value = _finite(reward, "reward")
        if not isinstance(clear, bool):
            raise ValueError("clear must be boolean")
        self._sync_connections()
        changes: dict[str, float] = {}
        for edge_id, edge in self.network.connections.items():
            if not edge.enabled:
                changes[edge_id] = 0.0
                continue
            proposed = edge.weight + self.learning_rate * reward_value * self.traces[edge_id]
            updated = max(-self.network.weight_limit, min(self.network.weight_limit, proposed))
            changes[edge_id] = updated - edge.weight
            edge.weight = updated
            if clear:
                self.traces[edge_id] = 0.0
        return changes

    def reset(self) -> None:
        """Clear all eligibility without changing network weights."""
        self._sync_connections()
        for edge_id in self.traces:
            self.traces[edge_id] = 0.0

    def snapshot(self) -> dict[str, object]:
        """Return a JSON-compatible checkpoint of rule parameters and traces."""
        self._sync_connections()
        return {
            "schema_version": self.schema_version,
            "learning_rate": self.learning_rate,
            "trace_decay": self.trace_decay,
            "trace_limit": self.trace_limit,
            "traces": dict(sorted(self.traces.items())),
        }

    def restore(self, data: Mapping[str, object]) -> None:
        """Restore a checkpoint only when its connection IDs match this network."""
        if data.get("schema_version") != self.schema_version:
            raise ValueError("unsupported eligibility-trace snapshot schema")
        trace_data = data.get("traces")
        if not isinstance(trace_data, Mapping):
            raise ValueError("snapshot traces must be a mapping")
        expected = set(self.network.connections)
        if set(trace_data) != expected:
            raise ValueError("snapshot connection IDs do not match the current network")
        restored: dict[str, float] = {}
        for edge_id, value in trace_data.items():
            score = _finite(value, f"trace {edge_id}")
            if abs(score) > self.trace_limit:
                raise ValueError(f"trace {edge_id} exceeds trace_limit")
            restored[str(edge_id)] = score
        self.traces = restored

    def _sync_connections(self) -> None:
        # New structural edges start with no credit; removed edges lose their trace.
        for edge_id in self.network.connections:
            self.traces.setdefault(edge_id, 0.0)
        for edge_id in tuple(self.traces):
            if edge_id not in self.network.connections:
                del self.traces[edge_id]
