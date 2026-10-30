"""Evidence-counted consolidation and optional decay for MNN connections.

This is an explicit engineering heuristic. It does not infer synaptic value
from inactivity: callers must record confirmed learning evidence, and decay
runs only when explicitly requested.
"""
from __future__ import annotations

import math
from typing import Mapping

from .mnn import MNN


class MNNSynapticConsolidator:
    """Protect repeatedly evidence-reinforced edges from bounded weight decay."""

    schema_version = 1

    def __init__(self, *, consolidation_observations: int = 5) -> None:
        if (
            isinstance(consolidation_observations, bool)
            or not isinstance(consolidation_observations, int)
            or consolidation_observations < 1
        ):
            raise ValueError("consolidation_observations must be a positive integer")
        self.consolidation_observations = consolidation_observations
        self.reinforcement_counts: dict[str, int] = {}
        self.evidence_by_edge: dict[str, list[str]] = {}
        self._operations: set[str] = set()

    def record_reinforcement(
        self,
        network: MNN,
        connection_ids: list[str] | tuple[str, ...],
        *,
        evidence_id: str,
        operation_id: str,
    ) -> bool:
        """Record externally grounded reinforcement once per operation.

        This method records evidence metadata only; it does not change weights.
        """
        if not isinstance(network, MNN):
            raise ValueError("network must be an MNN")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("evidence_id must be non-empty")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be non-empty")
        if isinstance(connection_ids, (str, bytes)) or not isinstance(connection_ids, (list, tuple)):
            raise ValueError("connection_ids must be a list or tuple")
        ids = tuple(connection_ids)
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("connection_ids must be non-empty and unique")
        if any(not isinstance(edge_id, str) or edge_id not in network.connections for edge_id in ids):
            raise ValueError("all connection IDs must exist in the network")
        if operation_id in self._operations:
            return False
        # Validate all inputs before mutating any state.
        for edge_id in ids:
            self.reinforcement_counts[edge_id] = self.reinforcement_counts.get(edge_id, 0) + 1
            history = self.evidence_by_edge.setdefault(edge_id, [])
            if evidence_id not in history:
                history.append(evidence_id)
        self._operations.add(operation_id)
        return True

    def stability(self, connection_id: str) -> float:
        """Return a bounded evidence-count score; not a probability of usefulness."""
        count = self.reinforcement_counts.get(connection_id, 0)
        return min(1.0, count / self.consolidation_observations)

    def apply_decay(
        self,
        network: MNN,
        *,
        decay_rate: float,
        protected_stability: float = 0.8,
    ) -> dict[str, float]:
        """Explicitly decay weights, attenuated by recorded consolidation.

        Edges at or above protected_stability are left unchanged. This operation
        never removes edges and never runs automatically during neural steps.
        """
        if not isinstance(network, MNN):
            raise ValueError("network must be an MNN")
        for name, value in (("decay_rate", decay_rate), ("protected_stability", protected_stability)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        changes: dict[str, float] = {}
        for edge_id, edge in network.connections.items():
            if not edge.enabled:
                continue
            stability = self.stability(edge_id)
            if stability >= float(protected_stability):
                changes[edge_id] = 0.0
                continue
            effective_rate = float(decay_rate) * (1.0 - stability)
            updated = edge.weight * (1.0 - effective_rate)
            changes[edge_id] = updated - edge.weight
            edge.weight = updated
        return changes

    def snapshot(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "consolidation_observations": self.consolidation_observations,
            "reinforcement_counts": dict(sorted(self.reinforcement_counts.items())),
            "evidence_by_edge": {key: list(value) for key, value in sorted(self.evidence_by_edge.items())},
            "operations": sorted(self._operations),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNSynapticConsolidator":
        if not isinstance(data, Mapping) or data.get("schema_version") != cls.schema_version:
            raise ValueError("unsupported synaptic-consolidator snapshot schema")
        result = cls(consolidation_observations=data["consolidation_observations"])
        counts = data.get("reinforcement_counts", {})
        evidence = data.get("evidence_by_edge", {})
        operations = data.get("operations", [])
        if not isinstance(counts, Mapping) or not isinstance(evidence, Mapping):
            raise ValueError("snapshot reinforcement and evidence data must be mappings")
        if not isinstance(operations, list) or any(not isinstance(item, str) or not item for item in operations):
            raise ValueError("snapshot operations must be a list of non-empty IDs")
        normalized_counts = {}
        normalized_evidence = {}
        for edge_id, count in counts.items():
            if not isinstance(edge_id, str) or not edge_id or isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError("invalid reinforcement count")
            normalized_counts[edge_id] = count
        for edge_id, items in evidence.items():
            if not isinstance(edge_id, str) or not edge_id or not isinstance(items, list):
                raise ValueError("invalid evidence history")
            if any(not isinstance(item, str) or not item for item in items):
                raise ValueError("evidence IDs must be non-empty strings")
            normalized_evidence[edge_id] = list(dict.fromkeys(items))
        if set(normalized_evidence) - set(normalized_counts):
            raise ValueError("evidence history references an uncounted connection")
        result.reinforcement_counts = normalized_counts
        result.evidence_by_edge = normalized_evidence
        result._operations = set(operations)
        return result
