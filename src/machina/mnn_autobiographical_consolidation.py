"""Explicit bridge from reviewed autobiographical signals to synaptic evidence.

The caller must approve the signal and map changed self-state paths to concrete
MNN connections. This adapter records consolidation evidence only; it does
not modify neural weights.
"""
from __future__ import annotations

from .mnn import MNN
from .mnn_autobiographical_learning import AutobiographicalLearningSignal
from .mnn_synaptic_consolidation import MNNSynapticConsolidator


class MNNAutobiographicalConsolidationAdapter:
    """Record externally approved autobiographical evidence for selected edges."""

    def record(
        self,
        signal: AutobiographicalLearningSignal,
        network: MNN,
        consolidator: MNNSynapticConsolidator,
        connection_ids: list[str] | tuple[str, ...],
        *,
        evidence_id: str,
        operation_id: str,
        accepted_for_reinforcement: bool,
    ) -> bool:
        if not isinstance(signal, AutobiographicalLearningSignal):
            raise TypeError("signal must be an AutobiographicalLearningSignal")
        if not isinstance(network, MNN):
            raise TypeError("network must be an MNN")
        if not isinstance(consolidator, MNNSynapticConsolidator):
            raise TypeError("consolidator must be an MNNSynapticConsolidator")
        if accepted_for_reinforcement is not True:
            raise ValueError("signal must be explicitly accepted for reinforcement")
        if signal.recommendation != "candidate_for_reinforcement":
            raise ValueError("only reinforcement-candidate signals can be recorded")
        if not isinstance(evidence_id, str) or evidence_id not in signal.evidence_refs:
            raise ValueError("evidence_id must belong to the reviewed signal")
        return consolidator.record_reinforcement(
            network,
            connection_ids,
            evidence_id=evidence_id,
            operation_id=operation_id,
        )
