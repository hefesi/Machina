"""Bridge the integrated MNN organism into the durable VirtualBrain cycle.

This adapter keeps MNNOrganism as the owner of neural, chemical, motivational,
and functional-continuity state. VirtualBrain remains the owner of cognitive
cycles and their append-only causal journal.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping

from .components import CognitionEngine, DeterministicCognition, _text
from .contracts import Artifact
from .mnn_organism import MNNOrganism


_SUPPORTED_FEATURES = {
    "text_length",
    "token_count",
    "digit_count",
    "punctuation_count",
    "goal_length",
    "memory_count",
    "source_reliability",
}


class MNNOrganismCognitionAdapter:
    """Run one MNNOrganism transition during each VirtualBrain cognition stage.

    The adapter exposes the organism's complete versioned snapshot in the
    existing understanding.mnn_signal.snapshot location. This deliberately
    reuses VirtualBrain's established journal-first persistence and restoration
    path instead of creating a parallel checkpoint mechanism.

    The wrapped cognition engine remains responsible for semantic analysis,
    candidate plans, and decisions. Neural telemetry is diagnostic evidence;
    it does not independently choose an action.
    """

    def __init__(
        self,
        organism: MNNOrganism,
        *,
        input_features: Mapping[str, str],
        base_engine: CognitionEngine | None = None,
        outcome_learning_rate: float = 0.01,
    ) -> None:
        if not isinstance(organism, MNNOrganism):
            raise TypeError("organism must be an MNNOrganism")
        if not input_features:
            raise ValueError("input_features must map at least one unit to a feature")
        unknown_features = set(input_features.values()) - _SUPPORTED_FEATURES
        if unknown_features:
            raise ValueError(f"unsupported MNN features: {sorted(unknown_features)}")
        unknown_units = set(input_features) - organism.network.units.keys()
        if unknown_units:
            raise ValueError(f"unknown MNN input units: {sorted(unknown_units)}")
        if (
            isinstance(outcome_learning_rate, bool)
            or not isinstance(outcome_learning_rate, (int, float))
            or not math.isfinite(outcome_learning_rate)
            or outcome_learning_rate < 0
        ):
            raise ValueError("outcome_learning_rate must be finite and non-negative")

        self.organism = organism
        self.input_features = dict(input_features)
        self.base_engine = base_engine or DeterministicCognition()
        self.outcome_learning_rate = float(outcome_learning_rate)

    @staticmethod
    def _features(
        observation: Artifact,
        retrieval: Artifact,
        goal: Artifact,
    ) -> dict[str, float]:
        text = _text(observation.data["content"])
        goal_text = _text(goal.data["description"])
        return {
            "text_length": min(len(text), 1000) / 1000.0,
            "token_count": min(len(re.findall(r"[\wÀ-ÿ]+", text)), 200) / 200.0,
            "digit_count": min(sum(char.isdigit() for char in text), 100) / 100.0,
            "punctuation_count": min(
                sum(not char.isalnum() and not char.isspace() for char in text), 100
            ) / 100.0,
            "goal_length": min(len(goal_text), 1000) / 1000.0,
            "memory_count": min(len(retrieval.data["memory_ids"]), 8) / 8.0,
            "source_reliability": float(observation.data.get("reliability", 1.0)),
        }

    def analyze(
        self,
        *,
        observation: Artifact,
        workspace: Artifact,
        retrieval: Artifact,
        goal: Artifact,
        request: Artifact,
    ) -> Mapping[str, object]:
        result = dict(
            self.base_engine.analyze(
                observation=observation,
                workspace=workspace,
                retrieval=retrieval,
                goal=goal,
                request=request,
            )
        )
        features = self._features(observation, retrieval, goal)
        inputs = {
            unit_id: features[feature]
            for unit_id, feature in self.input_features.items()
        }
        step = self.organism.step(inputs=inputs)

        understanding = dict(result.get("understanding", {}))
        understanding["mnn_signal"] = {
            "features": inputs,
            "activations": dict(step.neural_state),
            "timestep": step.timestep,
            "organism_state": {
                "chemical_state": dict(step.chemical_state),
                "prediction_error": step.prediction_error,
                "exploration_drive": step.exploration_drive,
                "plasticity_gain": step.plasticity_gain,
                "attention_gain": step.attention_gain,
                "weight_changes": dict(step.weight_changes),
                "motivation_urgencies": dict(step.motivation_urgencies),
            },
            "interpretation": (
                "computational organism telemetry; not a semantic conclusion "
                "or evidence of subjective experience"
            ),
            "snapshot": self.organism.snapshot(),
        }
        result["understanding"] = understanding
        return result

    def propose_evaluated_outcome(
        self, *, evaluation: Artifact, validation: Artifact
    ) -> Mapping[str, object]:
        """Prepare outcome-driven plasticity on a copy; do not mutate live state."""
        succeeded = bool(evaluation.data["success"])
        reward = 1.0 if succeeded else -1.0
        candidate = MNNOrganism.from_snapshot(self.organism.snapshot())
        deltas = candidate.network.apply_hebbian(
            learning_rate=self.outcome_learning_rate,
            reward=reward,
        )
        return {
            "success": succeeded,
            "reward": reward,
            "validation_status": validation.data["status"],
            "weight_deltas": deltas,
            "snapshot": candidate.snapshot(),
        }

    def restore_from_snapshot(self, snapshot: Mapping[str, object]) -> None:
        """Restore journaled organism state while retaining external memory.

        FragmentMemory is an independently owned persistence domain and is
        intentionally not embedded in MNNOrganism snapshots. Keep the attached
        memory object while restoring every field represented by the snapshot.
        """
        restored = MNNOrganism.from_snapshot(snapshot)
        missing = set(self.input_features) - restored.network.units.keys()
        if missing:
            raise ValueError(
                f"snapshot is missing configured input units: {sorted(missing)}"
            )

        self.organism.network = restored.network
        self.organism.signaling = restored.signaling
        self.organism.continuity = restored.continuity
        self.organism.chemical_inputs = restored.chemical_inputs
        self.organism.learning_rate = restored.learning_rate
        self.organism.motivation = restored.motivation
