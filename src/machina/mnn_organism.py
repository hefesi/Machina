"""Integrated persistent dynamics for the experimental MNN organism.

Coordinates neural state, virtual neuromodulation, and functional identity
history in one deterministic, resumable cycle. This is not evidence of
biological chemistry or consciousness.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Mapping

from .fragment_memory import FragmentMemory, MemoryFragment

from .chemical_signaling import ChemicalEvent, ChemicalSignaling
from .mnn import MNN
from .self_continuity import SelfContinuity


@dataclass(frozen=True)
class MemoryGuidance:
    """Auditable, bounded lexical evidence routed to one explicit MNN input."""

    query: str
    target_unit: str
    signal: float
    evidence_ids: tuple[str, ...]
    evidence_scores: Mapping[str, float]


@dataclass(frozen=True)
class OrganismStep:
    timestep: int
    neural_state: Mapping[str, float]
    chemical_state: Mapping[str, float]
    prediction_error: float
    exploration_drive: float
    plasticity_gain: float
    attention_gain: float
    weight_changes: Mapping[str, float]


class MNNOrganism:
    """Coordinate persistent MNN, chemical-control, and Self-continuity state."""

    SNAPSHOT_SCHEMA = 1

    def __init__(
        self,
        agent_id: str,
        network: MNN | None = None,
        signaling: ChemicalSignaling | None = None,
        continuity: SelfContinuity | None = None,
        *,
        chemical_inputs: Mapping[str, str] | None = None,
        learning_rate: float = 0.0,
        memory: FragmentMemory | None = None,
    ) -> None:
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id must be non-empty")
        if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
            raise ValueError("learning_rate must be a finite non-negative number")
        if not math.isfinite(learning_rate) or learning_rate < 0:
            raise ValueError("learning_rate must be a finite non-negative number")

        self.agent_id = agent_id
        self.network = network or MNN()
        self.signaling = signaling or ChemicalSignaling()
        self.continuity = continuity or SelfContinuity(agent_id)
        if self.continuity.agent_id != agent_id:
            raise ValueError("continuity agent_id must match organism agent_id")
        if self.network.timestep != self.signaling.state.timestep:
            raise ValueError("neural and chemical timesteps must match")
        self.chemical_inputs = dict(chemical_inputs or {})
        for chemical, unit_id in self.chemical_inputs.items():
            if chemical not in {"dopamine", "acetylcholine", "noradrenaline", "serotonin"}:
                raise ValueError(f"unknown chemical signal: {chemical}")
            if unit_id not in self.network.units:
                raise ValueError(f"chemical input unit does not exist: {unit_id}")
        self.learning_rate = float(learning_rate)
        self.memory = memory

    @property
    def timestep(self) -> int:
        return self.network.timestep

    def step(
        self,
        inputs: Mapping[str, float] | None = None,
        event: ChemicalEvent | None = None,
        *,
        memory_guidance: MemoryGuidance | None = None,
    ) -> OrganismStep:
        """Advance all coupled states exactly one deterministic logical tick."""
        neural_inputs = dict(inputs or {})
        unknown = set(neural_inputs) - self.network.units.keys()
        if unknown:
            raise ValueError(f"unknown neural input units: {sorted(unknown)}")
        for key, value in neural_inputs.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"input {key!r} must be a finite number")
        if memory_guidance is not None:
            if not isinstance(memory_guidance, MemoryGuidance):
                raise ValueError("memory_guidance must be a MemoryGuidance instance")
            if memory_guidance.target_unit not in self.network.units:
                raise ValueError("memory guidance target unit does not exist")
            if memory_guidance.target_unit in neural_inputs or memory_guidance.target_unit in self.chemical_inputs.values():
                raise ValueError("memory guidance target must not conflict with another input route")
            if not math.isfinite(memory_guidance.signal) or not 0.0 <= memory_guidance.signal <= 1.0:
                raise ValueError("memory guidance signal must be finite and within [0, 1]")
            neural_inputs[memory_guidance.target_unit] = memory_guidance.signal

        event = event or ChemicalEvent()
        chemical = self.signaling.step(event)
        for name, unit_id in self.chemical_inputs.items():
            neural_inputs[unit_id] = chemical.concentrations[name]

        neural_state = self.network.step(neural_inputs)
        weight_changes: Mapping[str, float] = {}
        if self.learning_rate:
            effective_rate = self.learning_rate * chemical.plasticity_gain
            weight_changes = self.network.apply_hebbian(
                learning_rate=effective_rate,
                reward=chemical.prediction_error,
            )

        self.continuity.record_event(
            "integrated_state_transition",
            "mnn_organism",
            reason=f"timestep={self.timestep}; prediction_error={chemical.prediction_error:.8f}",
        )
        if self.memory is not None:
            self.memory.add(
                content=(
                    f"MNN organism {self.agent_id} timestep {self.timestep} "
                    f"prediction error {chemical.prediction_error:.8f}"
                ),
                kind="episode",
                source_uri=f"machina://{self.agent_id}/experience/{self.timestep}",
                importance=min(1.0, abs(chemical.prediction_error)),
                confidence=1.0,
                tags=("mnn", "experience", "integrated-state"),
                metadata={
                    "agent_id": self.agent_id,
                    "timestep": self.timestep,
                    "neural_state": dict(neural_state),
                    "chemical_state": dict(chemical.concentrations),
                    "prediction_error": chemical.prediction_error,
                    "exploration_drive": chemical.exploration_drive,
                    "plasticity_gain": chemical.plasticity_gain,
                    "attention_gain": chemical.attention_gain,
                    "weight_changes": dict(weight_changes),
                },
                fragment_id=f"mnn-episode-{self.agent_id}-{self.timestep}",
            )
        return OrganismStep(
            timestep=self.timestep,
            neural_state=dict(neural_state),
            chemical_state=dict(chemical.concentrations),
            prediction_error=chemical.prediction_error,
            exploration_drive=chemical.exploration_drive,
            plasticity_gain=chemical.plasticity_gain,
            attention_gain=chemical.attention_gain,
            weight_changes=dict(weight_changes),
        )

    def recall_experiences(
        self, query: str, *, limit: int = 5, context: str | None = None
    ) -> list[MemoryFragment]:
        """Retrieve prior episodes from the attached persistent fragment archive."""
        if self.memory is None:
            raise RuntimeError("no FragmentMemory is attached to this organism")
        return self.memory.recall(query, limit=limit, context=context)

    def prepare_memory_guidance(
        self,
        query: str,
        *,
        target_unit: str,
        limit: int = 5,
        context: str | None = None,
        min_overlap: float = 0.10,
    ) -> MemoryGuidance:
        """Prepare explicit lexical memory evidence for a later neural step.

        The signal is a confidence-weighted mean token overlap, bounded to
        [0, 1]. No match yields zero. This is deliberately not semantic
        similarity, and preparation does not mutate the MNN or memory archive.
        """
        if self.memory is None:
            raise RuntimeError("no FragmentMemory is attached to this organism")
        if target_unit not in self.network.units:
            raise ValueError(f"unknown memory guidance target unit: {target_unit}")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if isinstance(min_overlap, bool) or not isinstance(min_overlap, (int, float)) or not math.isfinite(min_overlap) or not 0.0 <= min_overlap <= 1.0:
            raise ValueError("min_overlap must be finite and within [0, 1]")

        fragments = self.recall_experiences(query, limit=limit, context=context)
        def tokens(value: str) -> set[str]:
            return {token.casefold() for token in re.findall(r"\w+", value, flags=re.UNICODE) if len(token) > 1}

        query_tokens = tokens(query)
        scores: dict[str, float] = {}
        for fragment in fragments:
            searchable = " ".join((fragment.content, fragment.kind, " ".join(fragment.tags), str(dict(fragment.metadata))))
            overlap = len(query_tokens & tokens(searchable)) / len(query_tokens)
            if overlap >= float(min_overlap):
                scores[fragment.id] = min(1.0, max(0.0, overlap * fragment.confidence))
        signal = sum(scores.values()) / len(scores) if scores else 0.0
        return MemoryGuidance(
            query=query,
            target_unit=target_unit,
            signal=min(1.0, max(0.0, signal)),
            evidence_ids=tuple(scores),
            evidence_scores=dict(scores),
        )

    def snapshot(self) -> dict:
        """Return a JSON-compatible snapshot of the complete integrated state."""
        return {
            "schema_version": self.SNAPSHOT_SCHEMA,
            "agent_id": self.agent_id,
            "network": self.network.snapshot(),
            "signaling": self.signaling.snapshot(),
            "continuity": {
                "schema_version": self.continuity.schema_version,
                "commitments": dict(self.continuity.commitments),
                "event_history": [dict(item) for item in self.continuity.event_history],
                "component_versions": dict(self.continuity.component_versions),
            },
            "chemical_inputs": dict(self.chemical_inputs),
            "learning_rate": self.learning_rate,
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNOrganism":
        """Restore and validate an integrated state from its versioned snapshot."""
        if data.get("schema_version") != cls.SNAPSHOT_SCHEMA:
            raise ValueError("unsupported MNN organism snapshot schema")
        continuity_data = data.get("continuity")
        if not isinstance(continuity_data, Mapping):
            raise ValueError("continuity snapshot must be a mapping")
        continuity = SelfContinuity(
            agent_id=data["agent_id"],
            schema_version=continuity_data.get("schema_version", 1),
            commitments=dict(continuity_data.get("commitments", {})),
            event_history=[dict(item) for item in continuity_data.get("event_history", [])],
            component_versions=dict(continuity_data.get("component_versions", {})),
        )
        return cls(
            agent_id=data["agent_id"],
            network=MNN.from_snapshot(data["network"]),
            signaling=ChemicalSignaling.from_snapshot(data["signaling"]),
            continuity=continuity,
            chemical_inputs=data.get("chemical_inputs", {}),
            learning_rate=data.get("learning_rate", 0.0),
        )
