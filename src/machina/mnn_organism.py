"""Integrated persistent dynamics for the experimental MNN organism.

Coordinates neural state, virtual neuromodulation, and functional identity
history in one deterministic, resumable cycle. This is not evidence of
biological chemistry or consciousness.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import math
import re
from typing import Mapping

from .fragment_memory import FragmentMemory, MemoryFragment

from .chemical_signaling import ChemicalEvent, ChemicalSignaling
from .mnn import MNN
from .mnn_motivation import MotivationSystem
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
class DecisionOption:
    """One candidate action with externally estimated base utility and memory query."""

    action: str
    base_utility: float
    memory_query: str


@dataclass(frozen=True)
class DecisionAssessment:
    """Transparent comparison of candidate actions; not a claim of free will."""

    selected_action: str
    scores: Mapping[str, float]
    base_utilities: Mapping[str, float]
    memory_signals: Mapping[str, float]
    evidence_ids: Mapping[str, tuple[str, ...]]
    selected_guidance: MemoryGuidance


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
    motivation_urgencies: Mapping[str, float]


class MNNOrganism:
    """Coordinate persistent MNN, chemical-control, and Self-continuity state."""

    SNAPSHOT_SCHEMA = 2

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
        motivation: MotivationSystem | None = None,
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
        if motivation is not None and motivation.timestep != self.network.timestep:
            raise ValueError("neural, chemical, and motivational timesteps must match")
        self.chemical_inputs = dict(chemical_inputs or {})
        for chemical, unit_id in self.chemical_inputs.items():
            if chemical not in {"dopamine", "acetylcholine", "noradrenaline", "serotonin"}:
                raise ValueError(f"unknown chemical signal: {chemical}")
            if unit_id not in self.network.units:
                raise ValueError(f"chemical input unit does not exist: {unit_id}")
        self.learning_rate = float(learning_rate)
        self.memory = memory
        self.motivation = motivation

    @property
    def timestep(self) -> int:
        return self.network.timestep

    def step(
        self,
        inputs: Mapping[str, float] | None = None,
        event: ChemicalEvent | None = None,
        *,
        memory_guidance: MemoryGuidance | None = None,
        fulfillment: Mapping[str, float] | None = None,
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

        validated_fulfillment = (
            self.motivation.validate_fulfillment(fulfillment)
            if self.motivation is not None else {}
        )
        event = event or ChemicalEvent()
        if self.motivation is not None:
            event = replace(event, motivational_pressure=self.motivation.chemical_pressure)
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

        motivation_urgencies = (
            self.motivation.step(validated_fulfillment)
            if self.motivation is not None else {}
        )

        self.continuity.record_event(
            "integrated_state_transition",
            "mnn_organism",
            reason=(f"timestep={self.timestep}; prediction_error={chemical.prediction_error:.8f}; "
                    f"motivation={motivation_urgencies}"),
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
                    "motivation_urgencies": dict(motivation_urgencies),
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
            motivation_urgencies=dict(motivation_urgencies),
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
                contextual_weight = (
                    2.0 * self.memory.context_importance(fragment.id, context)
                    if context is not None else 1.0
                )
                scores[fragment.id] = min(
                    1.0,
                    max(0.0, overlap * fragment.confidence * contextual_weight),
                )
        signal = sum(scores.values()) / len(scores) if scores else 0.0
        return MemoryGuidance(
            query=query,
            target_unit=target_unit,
            signal=min(1.0, max(0.0, signal)),
            evidence_ids=tuple(scores),
            evidence_scores=dict(scores),
        )

    def assess_decisions(
        self,
        options: list[DecisionOption] | tuple[DecisionOption, ...],
        *,
        target_unit: str,
        context: str,
        memory_weight: float = 0.25,
        limit: int = 5,
    ) -> DecisionAssessment:
        """Rank explicit alternatives using base utility plus recalled evidence.

        The caller supplies candidate actions and their base utilities. Memory
        contributes a bounded, inspectable bonus; it does not invent options,
        estimate their base utility, or execute the selected action. Ties are
        resolved lexicographically for reproducibility.
        """
        if not isinstance(options, (list, tuple)) or not options:
            raise ValueError("options must be a non-empty list or tuple")
        if isinstance(memory_weight, bool) or not isinstance(memory_weight, (int, float)) or not math.isfinite(memory_weight) or memory_weight < 0:
            raise ValueError("memory_weight must be a finite non-negative number")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        actions: set[str] = set()
        scores: dict[str, float] = {}
        utilities: dict[str, float] = {}
        signals: dict[str, float] = {}
        evidence: dict[str, tuple[str, ...]] = {}
        guidances: dict[str, MemoryGuidance] = {}
        for option in options:
            if not isinstance(option, DecisionOption):
                raise ValueError("every option must be a DecisionOption")
            if not isinstance(option.action, str) or not option.action.strip() or option.action in actions:
                raise ValueError("action names must be unique non-empty strings")
            if isinstance(option.base_utility, bool) or not isinstance(option.base_utility, (int, float)) or not math.isfinite(option.base_utility):
                raise ValueError("base_utility must be finite")
            actions.add(option.action)
            guidance = self.prepare_memory_guidance(
                option.memory_query,
                target_unit=target_unit,
                limit=limit,
                context=context,
            )
            utility = float(option.base_utility)
            utilities[option.action] = utility
            signals[option.action] = guidance.signal
            evidence[option.action] = guidance.evidence_ids
            scores[option.action] = utility + float(memory_weight) * guidance.signal
            guidances[option.action] = guidance
        selected = min(scores, key=lambda action: (-scores[action], action))
        return DecisionAssessment(
            selected_action=selected,
            scores=dict(scores),
            base_utilities=dict(utilities),
            memory_signals=dict(signals),
            evidence_ids=dict(evidence),
            selected_guidance=guidances[selected],
        )

    def evaluate_memory_guidance(
        self,
        guidance: MemoryGuidance,
        outcomes: Mapping[str, bool],
        *,
        context: str,
        operation_id: str,
        strength: float = 0.10,
    ) -> tuple[dict[str, float], bool]:
        """Feed externally evaluated usefulness back into context-specific memory.

        Only evidence cited by this guidance can be updated. The evaluator must
        supply explicit boolean labels; this method never infers success from
        activation magnitude or reward prediction error. operation_id makes
        retries idempotent in FragmentMemory.
        """
        if self.memory is None:
            raise RuntimeError("no FragmentMemory is attached to this organism")
        if not isinstance(guidance, MemoryGuidance):
            raise ValueError("guidance must be a MemoryGuidance instance")
        if not isinstance(outcomes, Mapping) or not outcomes:
            raise ValueError("outcomes must be a non-empty mapping")
        unknown = set(outcomes) - set(guidance.evidence_ids)
        if unknown:
            raise ValueError(f"feedback references fragments outside this guidance: {sorted(unknown)}")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        if any(not isinstance(value, bool) for value in outcomes.values()):
            raise ValueError("every outcome must be boolean")
        return self.memory.apply_context_feedback_batch(
            outcomes,
            context=context,
            operation_id=operation_id,
            strength=strength,
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
            "motivation": self.motivation.snapshot() if self.motivation is not None else None,
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNOrganism":
        """Restore and validate an integrated state from its versioned snapshot."""
        schema_version = data.get("schema_version")
        if schema_version not in {1, cls.SNAPSHOT_SCHEMA}:
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
            motivation=(
                MotivationSystem.from_snapshot(data["motivation"])
                if data.get("motivation") is not None else None
            ),
        )
