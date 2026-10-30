"""Auditable, reversible proposals for long-term MNN synaptic plasticity.

Proposal generation is observational. Applying a proposal is a separate,
explicit operation that checks the exact topology and base weights. The
controller is an in-memory guard; persist its snapshot alongside the network
snapshot if rollback must survive process restarts.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Mapping
from types import MappingProxyType

from .mnn import MNN


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


@dataclass(frozen=True)
class MNNPlasticityProposal:
    proposal_id: str
    topology_fingerprint: str
    base_weights: Mapping[str, float]
    proposed_weights: Mapping[str, float]
    deltas: Mapping[str, float]
    learning_rate: float
    reward: float
    max_delta: float


class MNNPlasticityController:
    """Prepare, explicitly apply, and conditionally roll back weight changes."""

    schema_version = 1

    def __init__(self) -> None:
        self._applied: dict[str, dict[str, float]] = {}

    @staticmethod
    def _topology_fingerprint(network: MNN) -> str:
        topology = [
            (edge.id, edge.source, edge.target, bool(edge.enabled))
            for edge in sorted(network.connections.values(), key=lambda item: item.id)
        ]
        encoded = json.dumps(topology, separators=(",", ":"), ensure_ascii=True).encode()
        return hashlib.sha256(encoded).hexdigest()

    def propose_hebbian(
        self,
        network: MNN,
        *,
        proposal_id: str,
        learning_rate: float,
        reward: float,
        max_delta: float = 0.05,
        connection_ids: tuple[str, ...] | list[str] | None = None,
    ) -> MNNPlasticityProposal:
        """Calculate bounded reward-modulated Hebbian changes without mutation."""
        if not isinstance(network, MNN):
            raise ValueError("network must be an MNN")
        if not isinstance(proposal_id, str) or not proposal_id.strip():
            raise ValueError("proposal_id must be non-empty")
        if proposal_id in self._applied:
            raise ValueError("proposal_id has already been applied")
        rate = _finite(learning_rate, "learning_rate")
        reward_value = _finite(reward, "reward")
        delta_limit = _finite(max_delta, "max_delta")
        if rate < 0.0:
            raise ValueError("learning_rate cannot be negative")
        if not 0.0 <= reward_value <= 1.0:
            raise ValueError("reward must be within [0, 1]")
        if not 0.0 <= delta_limit <= 1.0:
            raise ValueError("max_delta must be within [0, 1]")
        if connection_ids is None:
            selected = tuple(sorted(network.connections))
        else:
            if isinstance(connection_ids, (str, bytes)) or not isinstance(connection_ids, (list, tuple)):
                raise ValueError("connection_ids must be a list or tuple")
            selected = tuple(connection_ids)
            if not selected or len(set(selected)) != len(selected):
                raise ValueError("connection_ids must be non-empty and unique")
            if any(not isinstance(item, str) or item not in network.connections for item in selected):
                raise ValueError("all selected connection IDs must exist")
        base: dict[str, float] = {}
        proposed: dict[str, float] = {}
        deltas: dict[str, float] = {}
        for edge_id in selected:
            edge = network.connections[edge_id]
            base[edge_id] = edge.weight
            if not edge.enabled:
                updated = edge.weight
            else:
                pre = _finite(network.units[edge.source].state, f"source state for {edge_id}")
                post = _finite(network.units[edge.target].state, f"target state for {edge_id}")
                raw_delta = rate * reward_value * pre * post
                bounded_delta = max(-delta_limit, min(delta_limit, raw_delta))
                updated = max(-network.weight_limit, min(network.weight_limit, edge.weight + bounded_delta))
            proposed[edge_id] = updated
            deltas[edge_id] = updated - edge.weight
        return MNNPlasticityProposal(
            proposal_id=proposal_id,
            topology_fingerprint=self._topology_fingerprint(network),
            base_weights=MappingProxyType(dict(base)),
            proposed_weights=MappingProxyType(dict(proposed)),
            deltas=MappingProxyType(dict(deltas)),
            learning_rate=rate,
            reward=reward_value,
            max_delta=delta_limit,
        )

    def apply(self, network: MNN, proposal: MNNPlasticityProposal) -> dict[str, float]:
        """Apply only if topology and every selected base weight still match."""
        if not isinstance(network, MNN) or not isinstance(proposal, MNNPlasticityProposal):
            raise ValueError("network and proposal have invalid types")
        if proposal.proposal_id in self._applied:
            raise ValueError("proposal has already been applied")
        if self._topology_fingerprint(network) != proposal.topology_fingerprint:
            raise ValueError("network topology changed since proposal creation")
        if set(proposal.base_weights) != set(proposal.proposed_weights):
            raise ValueError("proposal weight maps do not match")
        for edge_id, base_weight in proposal.base_weights.items():
            if edge_id not in network.connections:
                raise ValueError(f"proposal references missing connection: {edge_id}")
            if network.connections[edge_id].weight != base_weight:
                raise ValueError(f"connection {edge_id} changed since proposal creation")
        # Validate all proposed values before changing any connection.
        for edge_id, value in proposal.proposed_weights.items():
            if not math.isfinite(value) or abs(value) > network.weight_limit:
                raise ValueError(f"proposed weight for {edge_id} is outside network bounds")
        for edge_id, value in proposal.proposed_weights.items():
            network.connections[edge_id].weight = value
        self._applied[proposal.proposal_id] = {
            "base": dict(proposal.base_weights),
            "proposed": dict(proposal.proposed_weights),
        }
        return dict(proposal.deltas)

    def rollback(self, network: MNN, proposal_id: str) -> dict[str, float]:
        """Restore original weights only if no later change touched those edges."""
        if not isinstance(network, MNN):
            raise ValueError("network must be an MNN")
        if not isinstance(proposal_id, str) or proposal_id not in self._applied:
            raise ValueError("proposal is not applied or is unknown")
        record = self._applied[proposal_id]
        original = record["base"]
        proposed = record["proposed"]
        for edge_id, proposed_weight in proposed.items():
            if edge_id not in network.connections:
                raise ValueError(f"connection {edge_id} no longer exists")
            if network.connections[edge_id].weight != proposed_weight:
                raise ValueError("applied weights no longer match; refusing unsafe rollback")
        changes = {
            edge_id: original[edge_id] - network.connections[edge_id].weight
            for edge_id in original
        }
        for edge_id, base_weight in original.items():
            network.connections[edge_id].weight = base_weight
        del self._applied[proposal_id]
        return changes

    def snapshot(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "applied": {
                key: {
                    "base": dict(sorted(value["base"].items())),
                    "proposed": dict(sorted(value["proposed"].items())),
                }
                for key, value in sorted(self._applied.items())
            },
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNPlasticityController":
        if not isinstance(data, Mapping) or data.get("schema_version") != cls.schema_version:
            raise ValueError("unsupported plasticity-controller snapshot schema")
        applied = data.get("applied", {})
        if not isinstance(applied, Mapping):
            raise ValueError("applied proposal history must be a mapping")
        controller = cls()
        restored = {}
        for proposal_id, weights in applied.items():
            if not isinstance(proposal_id, str) or not proposal_id or not isinstance(weights, Mapping):
                raise ValueError("invalid applied proposal record")
            if not isinstance(weights.get("base"), Mapping) or not isinstance(weights.get("proposed"), Mapping):
                raise ValueError("applied proposal must contain base and proposed weights")
            if set(weights["base"]) != set(weights["proposed"]):
                raise ValueError("base and proposed connection IDs must match")
            normalized = {"base": {}, "proposed": {}}
            for kind in ("base", "proposed"):
                for edge_id, weight in weights[kind].items():
                    if not isinstance(edge_id, str) or not edge_id:
                        raise ValueError("invalid connection ID in applied proposal")
                    normalized[kind][edge_id] = _finite(weight, f"restored {kind} weight for {edge_id}")
            restored[proposal_id] = normalized
        controller._applied = restored
        return controller
