"""Experience -> delayed outcome -> plasticity cycle for the MNN.

Activity is separated from its consequence. Each step accumulates per-edge
eligibility traces with a neutral reward, so weights are not changed before an
outcome is known. Resolving the experience later applies the reward prediction
error to the traces that were active during the experience.

This is a computational credit-assignment mechanism, not a biological
simulation and not evidence of learning general tasks.
"""
from __future__ import annotations

import json
import math
import os
import tempfile
from pathlib import Path
from typing import Mapping

from .mnn import MNN
from .mnn_reward import RewardModulator
from .mnn_structure import ActivityGrowthPolicy


def _finite_number(value: float, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be finite")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be finite") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _pending_limit(value: int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError("max_pending_steps must be a positive integer or None")
    return value


def _positive_limit(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer or None")
    return value


class MNNExperienceCycle:
    """Coordinate network steps, eligibility accumulation, and delayed outcomes."""

    def __init__(
        self,
        network: MNN,
        *,
        modulator: RewardModulator | None = None,
        learning_rate: float = 0.1,
        max_pending_steps: int | None = None,
        growth_policy: ActivityGrowthPolicy | None = None,
        growth_min_reward: float = 0.0,
        prune_after_negative_outcomes: int | None = None,
    ) -> None:
        if not isinstance(network, MNN):
            raise ValueError("network must be an MNN instance")
        if modulator is not None and not isinstance(modulator, RewardModulator):
            raise ValueError("modulator must be a RewardModulator instance")
        if growth_policy is not None and not isinstance(
            growth_policy, ActivityGrowthPolicy
        ):
            raise ValueError("growth_policy must be an ActivityGrowthPolicy instance")
        if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
            raise ValueError("learning_rate must be finite and non-negative")
        self.learning_rate = float(learning_rate)
        if not math.isfinite(self.learning_rate) or self.learning_rate < 0:
            raise ValueError("learning_rate must be finite and non-negative")
        self.max_pending_steps = _pending_limit(max_pending_steps)
        self.growth_policy = growth_policy
        self.growth_min_reward = _finite_number(
            growth_min_reward, "growth_min_reward"
        )
        self.prune_after_negative_outcomes = _positive_limit(
            prune_after_negative_outcomes,
            "prune_after_negative_outcomes",
        )
        if (
            self.prune_after_negative_outcomes is not None
            and self.growth_policy is None
        ):
            raise ValueError(
                "prune_after_negative_outcomes requires a growth_policy"
            )
        self.structural_utility: dict[str, int] = {}
        self.network = network
        self.modulator = modulator or RewardModulator()
        self.pending_steps = 0

    def step(self, inputs: Mapping[str, float] | None = None) -> dict[str, float]:
        """Advance the network and accumulate eligibility without outcome credit."""
        if (
            self.max_pending_steps is not None
            and self.pending_steps >= self.max_pending_steps
        ):
            raise RuntimeError(
                f"experience exceeded max pending steps ({self.max_pending_steps})"
            )
        outputs = self.network.step(inputs)
        neutral_reward = self.modulator.baseline
        if neutral_reward is None:
            neutral_reward = 0.0
        self.modulator.update(
            self.network,
            reward=neutral_reward,
            learning_rate=self.learning_rate,
        )
        self.pending_steps += 1
        return outputs

    def resolve(self, reward: float) -> dict:
        """Apply a delayed outcome to eligible edges, then close the experience."""
        if self.pending_steps == 0:
            raise RuntimeError("cannot resolve an outcome before at least one step")
        changes = self.modulator.update(
            self.network,
            reward=reward,
            learning_rate=self.learning_rate,
        )
        reward_value = float(reward)
        pruned_connections = self._prune_weak_grown_connections(reward_value)
        grown_connections = []
        if (
            self.growth_policy is not None
            and reward_value >= self.growth_min_reward
        ):
            grown_connections = [
                {
                    "id": item.connection.id,
                    "source": item.connection.source,
                    "target": item.connection.target,
                    "weight": item.connection.weight,
                    "score": item.score,
                }
                for item in self.growth_policy.grow(self.network)
            ]
            if self.prune_after_negative_outcomes is not None:
                for item in grown_connections:
                    self.structural_utility[item["id"]] = 0
        result = {
            "reward": reward_value,
            "pending_steps": self.pending_steps,
            "weight_changes": changes,
            "grown_connections": grown_connections,
            "pruned_connections": pruned_connections,
            "network_snapshot": self.network.snapshot(),
            "modulator_snapshot": self.modulator.snapshot(),
        }
        self.modulator.reset_traces()
        self.pending_steps = 0
        return result

    def abort(self) -> dict:
        """Discard a pending experience without applying any outcome.

        Weights and the reward baseline are preserved; only the eligibility
        traces accumulated for this experience are cleared. This is the explicit
        lifecycle operation for outcomes that will never arrive.
        """
        if self.pending_steps == 0:
            raise RuntimeError("cannot abort an outcome before at least one step")
        result = {
            "pending_steps": self.pending_steps,
            "discarded_edges": sorted(self.modulator.eligibility),
            "network_snapshot": self.network.snapshot(),
            "modulator_snapshot": self.modulator.snapshot(),
        }
        self.modulator.reset_traces()
        self.pending_steps = 0
        return result

    def _prune_weak_grown_connections(self, reward: float) -> list[str]:
        """Track negative outcomes for grown edges and prune them when exhausted.

        Positive outcomes reset an edge's consecutive-negative counter; neutral
        outcomes leave it unchanged. Only edges created by the configured growth
        policy are considered.
        """
        if self.prune_after_negative_outcomes is None:
            return []
        stale = [
            edge_id
            for edge_id in self.structural_utility
            if edge_id not in self.network.connections
        ]
        for edge_id in stale:
            del self.structural_utility[edge_id]
        if reward < 0:
            for edge_id in self.structural_utility:
                self.structural_utility[edge_id] -= 1
        elif reward > 0:
            for edge_id in self.structural_utility:
                self.structural_utility[edge_id] = 0
        pruned = [
            edge_id
            for edge_id, utility in sorted(self.structural_utility.items())
            if utility <= -self.prune_after_negative_outcomes
        ]
        for edge_id in pruned:
            self.network.remove_connection(edge_id)
            self.modulator.eligibility.pop(edge_id, None)
            del self.structural_utility[edge_id]
        return pruned

    def snapshot(self) -> dict:
        """Return JSON-compatible state, including an in-flight experience."""
        return {
            "schema_version": 1,
            "learning_rate": self.learning_rate,
            "max_pending_steps": self.max_pending_steps,
            "growth_policy": (
                None
                if self.growth_policy is None
                else self.growth_policy.snapshot()
            ),
            "growth_min_reward": self.growth_min_reward,
            "prune_after_negative_outcomes": self.prune_after_negative_outcomes,
            "structural_utility": dict(sorted(self.structural_utility.items())),
            "pending_steps": self.pending_steps,
            "network": self.network.snapshot(),
            "modulator": self.modulator.snapshot(),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNExperienceCycle":
        if not isinstance(data, Mapping):
            raise ValueError("experience-cycle snapshot must be a mapping")
        if data.get("schema_version") != 1:
            raise ValueError("unsupported MNN experience-cycle snapshot schema")
        required = {"schema_version", "learning_rate", "pending_steps", "network", "modulator"}
        missing = required - set(data)
        if missing:
            raise ValueError(
                f"experience-cycle snapshot is missing fields: {', '.join(sorted(missing))}"
            )
        allowed = required | {
            "max_pending_steps",
            "growth_policy",
            "growth_min_reward",
            "prune_after_negative_outcomes",
            "structural_utility",
        }
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(
                f"experience-cycle snapshot has unknown fields: {', '.join(sorted(unknown))}"
            )
        network_data, modulator_data = data["network"], data["modulator"]
        if not isinstance(network_data, Mapping):
            raise ValueError("experience-cycle network snapshot must be a mapping")
        if not isinstance(modulator_data, Mapping):
            raise ValueError("experience-cycle modulator snapshot must be a mapping")
        network = MNN.from_snapshot(network_data)
        modulator = RewardModulator.from_snapshot(modulator_data)
        unknown_edges = set(modulator.eligibility) - set(network.connections)
        if unknown_edges:
            raise ValueError(
                f"eligibility snapshot references unknown edges: {sorted(unknown_edges)}"
            )
        pending_steps = data["pending_steps"]
        if (
            isinstance(pending_steps, bool)
            or not isinstance(pending_steps, int)
            or pending_steps < 0
        ):
            raise ValueError("pending_steps must be a non-negative integer")
        if pending_steps == 0 and modulator.eligibility:
            raise ValueError("closed experience cannot contain eligibility traces")
        max_pending_steps = _pending_limit(data.get("max_pending_steps"))
        if max_pending_steps is not None and pending_steps > max_pending_steps:
            raise ValueError("pending_steps cannot exceed max_pending_steps")
        growth_data = data.get("growth_policy")
        if growth_data is None:
            growth_policy = None
        elif not isinstance(growth_data, Mapping):
            raise ValueError("growth_policy snapshot must be a mapping")
        else:
            growth_policy = ActivityGrowthPolicy.from_snapshot(growth_data)
        prune_after = _positive_limit(
            data.get("prune_after_negative_outcomes"),
            "prune_after_negative_outcomes",
        )
        utility_data = data.get("structural_utility", {})
        if not isinstance(utility_data, Mapping):
            raise ValueError("structural_utility must be a mapping")
        structural_utility: dict[str, int] = {}
        for edge_id, utility in utility_data.items():
            if not isinstance(edge_id, str) or not edge_id:
                raise ValueError("structural_utility keys must be edge IDs")
            if isinstance(utility, bool) or not isinstance(utility, int):
                raise ValueError(
                    f"structural_utility for {edge_id!r} must be an integer"
                )
            if utility > 0:
                raise ValueError(
                    f"structural_utility for {edge_id!r} cannot be positive"
                )
            structural_utility[edge_id] = utility
        unknown_utility_edges = set(structural_utility) - set(network.connections)
        if unknown_utility_edges:
            raise ValueError(
                "structural_utility references unknown edges: "
                f"{sorted(unknown_utility_edges)}"
            )
        if prune_after is not None and any(
            utility <= -prune_after for utility in structural_utility.values()
        ):
            raise ValueError(
                "structural_utility contains an edge that should have been pruned"
            )
        cycle = cls(
            network,
            modulator=modulator,
            learning_rate=data["learning_rate"],
            max_pending_steps=max_pending_steps,
            growth_policy=growth_policy,
            growth_min_reward=data.get("growth_min_reward", 0.0),
            prune_after_negative_outcomes=prune_after,
        )
        cycle.structural_utility = structural_utility
        cycle.pending_steps = pending_steps
        return cycle


class MNNExperienceCheckpointStore:
    """Atomically persist a complete experience cycle, including pending traces.

    Saving an in-flight experience lets a restarted process apply the delayed
    outcome exactly once to the connections that were active before the restart.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, cycle: MNNExperienceCycle) -> None:
        """Validate and atomically persist the full cycle snapshot."""
        if not isinstance(cycle, MNNExperienceCycle):
            raise ValueError("cycle must be an MNNExperienceCycle instance")
        snapshot = cycle.snapshot()
        # Validate the serialized contract before replacing a good checkpoint.
        MNNExperienceCycle.from_snapshot(snapshot)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = temporary.name
                json.dump(snapshot, temporary, ensure_ascii=False, sort_keys=True)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    def load(self) -> MNNExperienceCycle:
        """Load a checkpoint and validate it through the cycle snapshot contract."""
        with self.path.open("r", encoding="utf-8") as source:
            try:
                snapshot = json.load(source)
            except json.JSONDecodeError as error:
                raise ValueError(
                    f"invalid MNN experience checkpoint JSON: {self.path}"
                ) from error
        if not isinstance(snapshot, dict):
            raise ValueError("MNN experience checkpoint must contain a JSON object")
        return MNNExperienceCycle.from_snapshot(snapshot)
