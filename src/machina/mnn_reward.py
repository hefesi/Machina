"""Reward-modulated eligibility traces for delayed learning in the MNN.

This is a computational learning signal inspired by neuromodulation, not a
biochemical simulation and not evidence of subjective feeling. A reward can
reinforce or weaken recently eligible connections even when the outcome arrives
after the activity that created the eligibility.
"""
from __future__ import annotations

import math
from typing import Mapping

from .mnn import MNN


def _finite(value: float, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


class RewardModulator:
    """Maintain per-edge eligibility and apply reward-prediction-error updates.

    For edge e at time t:
      eligibility[e] = decay * eligibility[e] + pre[e] * post[e]
      delta_w[e] = learning_rate * (reward - baseline) * eligibility[e]

    The baseline is updated after computing the prediction error. All weight
    changes remain bounded by the network's configured weight_limit.
    """

    def __init__(self, *, trace_decay: float = 0.9, baseline_rate: float = 0.05) -> None:
        self.trace_decay = _finite(trace_decay, "trace_decay")
        self.baseline_rate = _finite(baseline_rate, "baseline_rate")
        if not 0.0 <= self.trace_decay <= 1.0:
            raise ValueError("trace_decay must be between 0 and 1")
        if not 0.0 < self.baseline_rate <= 1.0:
            raise ValueError("baseline_rate must be in (0, 1]")
        self.baseline: float | None = None
        self.eligibility: dict[str, float] = {}

    def update(
        self,
        network: MNN,
        *,
        reward: float,
        learning_rate: float = 0.1,
    ) -> dict[str, float]:
        """Accumulate recent co-activity and modulate weights by prediction error."""
        reward_value = _finite(reward, "reward")
        rate = _finite(learning_rate, "learning_rate")
        if rate < 0:
            raise ValueError("learning_rate cannot be negative")

        # Remove traces for edges that no longer exist; disabled edges do not
        # accumulate or learn, but their old trace is cleared to avoid surprises.
        live_ids = set(network.connections)
        for edge_id in list(self.eligibility):
            if edge_id not in live_ids or not network.connections[edge_id].enabled:
                self.eligibility.pop(edge_id, None)

        for edge_id, edge in network.connections.items():
            if edge.enabled:
                previous = self.eligibility.get(edge_id, 0.0)
                coactivity = network.units[edge.source].state * network.units[edge.target].state
                self.eligibility[edge_id] = self.trace_decay * previous + coactivity

        prediction_error = reward_value if self.baseline is None else reward_value - self.baseline
        changes: dict[str, float] = {}
        for edge_id, trace in self.eligibility.items():
            edge = network.connections[edge_id]
            proposed = edge.weight + rate * prediction_error * trace
            updated = max(-network.weight_limit, min(network.weight_limit, proposed))
            changes[edge_id] = updated - edge.weight
            edge.weight = updated

        if self.baseline is None:
            self.baseline = reward_value
        else:
            self.baseline += self.baseline_rate * (reward_value - self.baseline)
        return changes

    def reset_traces(self) -> None:
        """Clear short-lived eligibility while retaining the learned reward baseline."""
        self.eligibility.clear()

    def snapshot(self) -> dict:
        """Return JSON-compatible state for checkpointing the modulator."""
        return {
            "schema_version": 1,
            "trace_decay": self.trace_decay,
            "baseline_rate": self.baseline_rate,
            "baseline": self.baseline,
            "eligibility": dict(sorted(self.eligibility.items())),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "RewardModulator":
        if data.get("schema_version") != 1:
            raise ValueError("unsupported reward-modulator snapshot schema")
        modulator = cls(
            trace_decay=data["trace_decay"],
            baseline_rate=data["baseline_rate"],
        )
        baseline = data.get("baseline")
        modulator.baseline = None if baseline is None else _finite(baseline, "baseline")
        traces = data.get("eligibility", {})
        if not isinstance(traces, Mapping):
            raise ValueError("eligibility must be a mapping")
        modulator.eligibility = {
            str(key): _finite(value, f"eligibility {key}") for key, value in traces.items()
        }
        return modulator
