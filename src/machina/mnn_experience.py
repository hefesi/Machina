"""A small experience -> delayed outcome -> plasticity cycle for the MNN.

The cycle separates activity from outcome: each step accumulates eligibility
using a neutral reward equal to the current baseline; resolving an outcome later
applies its prediction error to the accumulated traces.
"""
from __future__ import annotations

import math
from typing import Mapping

from .mnn import MNN
from .mnn_reward import RewardModulator


class MNNExperienceCycle:
    """Coordinate neural steps, eligibility accumulation, and delayed outcomes."""

    def __init__(self, network: MNN, *, modulator: RewardModulator | None = None,
                 learning_rate: float = 0.1) -> None:
        self.network = network
        self.modulator = modulator or RewardModulator()
        self.learning_rate = float(learning_rate)
        if not math.isfinite(self.learning_rate) or self.learning_rate < 0:
            raise ValueError("learning_rate must be finite and non-negative")
        self.pending_steps = 0

    def step(self, inputs: Mapping[str, float] | None = None) -> dict[str, float]:
        """Advance the network and accumulate eligibility without outcome credit."""
        outputs = self.network.step(inputs)
        neutral_reward = self.modulator.baseline
        if neutral_reward is None:
            neutral_reward = 0.0
        self.modulator.update(self.network, reward=neutral_reward,
                              learning_rate=self.learning_rate)
        self.pending_steps += 1
        return outputs

    def resolve(self, reward: float) -> dict:
        """Apply a delayed outcome to eligible edges, then close the episode."""
        if self.pending_steps == 0:
            raise RuntimeError("cannot resolve an outcome before at least one step")
        changes = self.modulator.update(self.network, reward=reward,
                                        learning_rate=self.learning_rate)
        result = {
            "reward": float(reward),
            "pending_steps": self.pending_steps,
            "weight_changes": changes,
            "network_snapshot": self.network.snapshot(),
            "modulator_snapshot": self.modulator.snapshot(),
        }
        self.modulator.reset_traces()
        self.pending_steps = 0
        return result

    def snapshot(self) -> dict:
        """Return JSON-compatible state, including an in-flight experience."""
        return {
            "schema_version": 1,
            "learning_rate": self.learning_rate,
            "pending_steps": self.pending_steps,
            "network": self.network.snapshot(),
            "modulator": self.modulator.snapshot(),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNExperienceCycle":
        if data.get("schema_version") != 1:
            raise ValueError("unsupported MNN experience-cycle snapshot schema")
        network = MNN.from_snapshot(data["network"])
        modulator = RewardModulator.from_snapshot(data["modulator"])
        unknown_edges = set(modulator.eligibility) - set(network.connections)
        if unknown_edges:
            raise ValueError(f"eligibility snapshot references unknown edges: {sorted(unknown_edges)}")
        cycle = cls(network, modulator=modulator, learning_rate=data["learning_rate"])
        pending_steps = data["pending_steps"]
        if isinstance(pending_steps, bool) or not isinstance(pending_steps, int) or pending_steps < 0:
            raise ValueError("pending_steps must be a non-negative integer")
        if pending_steps == 0 and modulator.eligibility:
            raise ValueError("closed experience cannot contain eligibility traces")
        cycle.pending_steps = pending_steps
        return cycle
