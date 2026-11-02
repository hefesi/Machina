'''Optional adapter exposing MNN signals inside the VirtualBrain cycle.

The adapter does not claim numeric activations are semantic reasoning. It wraps
an existing cognition engine, runs configured features through an MNN, and
stores the trace in the normal cognitive artifact.
'''
from __future__ import annotations

import math
import re
from collections.abc import Mapping

from .components import CognitionEngine, DeterministicCognition, _text
from .contracts import Artifact, ContractKind
from .mnn import MNN


_SUPPORTED_FEATURES = {
    "text_length", "token_count", "digit_count", "punctuation_count",
    "goal_length", "memory_count", "source_reliability",
}


class MNNCognitionAdapter:
    """Decorate cognition with a transparent MNN feature-processing pass.

    input_features maps MNN input-unit IDs to deterministic feature names.
    The wrapped engine remains responsible for candidate plans and decisions.
    """

    def __init__(
        self,
        network: MNN,
        *,
        input_features: Mapping[str, str],
        base_engine: CognitionEngine | None = None,
        learning_rate: float = 0.01,
    ) -> None:
        if not input_features:
            raise ValueError("input_features must map at least one unit to a feature")
        unknown_features = set(input_features.values()) - _SUPPORTED_FEATURES
        if unknown_features:
            raise ValueError(f"unsupported MNN features: {sorted(unknown_features)}")
        unknown_units = set(input_features) - network.units.keys()
        if unknown_units:
            raise ValueError(f"unknown MNN input units: {sorted(unknown_units)}")
        self.network = network
        self.input_features = dict(input_features)
        self.base_engine = base_engine or DeterministicCognition()
        self.learning_rate = float(learning_rate)
        if self.learning_rate < 0 or not math.isfinite(self.learning_rate):
            raise ValueError("learning_rate must be finite and non-negative")

    def propose_evaluated_outcome(
        self, *, evaluation: Artifact, validation: Artifact
    ) -> Mapping[str, object]:
        """Compute a bounded plasticity proposal without mutating live state.

        The orchestrator first persists this proposal in the append-only journal,
        then commits the saved snapshot back into the adapter. This ordering
        avoids changing in-memory weights if the journal append fails.
        """
        if evaluation.kind != ContractKind.EVALUATION:
            raise ValueError("evaluation must be an EVALUATION artifact")
        if validation.kind != ContractKind.VALIDATION_RESULT:
            raise ValueError("validation must be a VALIDATION_RESULT artifact")
        if evaluation.cycle_id != validation.cycle_id or evaluation.id not in validation.input_refs:
            raise ValueError("validation must preserve the evaluated outcome in the same cycle")
        succeeded = evaluation.data.get("success")
        if not isinstance(succeeded, bool):
            raise ValueError("evaluation success must be an explicit boolean")
        prediction_error = evaluation.data.get("prediction_error")
        if (
            isinstance(prediction_error, bool)
            or not isinstance(prediction_error, (int, float))
            or not math.isfinite(prediction_error)
            or not 0.0 <= prediction_error <= 1.0
        ):
            raise ValueError("prediction_error must be finite and within [0, 1]")
        reward = 1.0 if succeeded else -1.0
        candidate = MNN.from_snapshot(self.network.snapshot())
        weight_deltas = candidate.apply_hebbian(
            learning_rate=self.learning_rate,
            reward=reward,
        )
        return {
            "success": succeeded,
            "reward": reward,
            "prediction_error": float(prediction_error),
            "expected_outcome": evaluation.data["expected_outcome"],
            "actual_outcome": evaluation.data["actual_outcome"],
            "evaluation_ref": evaluation.id,
            "validation_ref": validation.id,
            "validation_status": validation.data["status"],
            "evidence_refs": [evaluation.id, validation.id, *evaluation.source_refs],
            "weight_deltas": weight_deltas,
            "snapshot": candidate.snapshot(),
        }

    def restore_from_snapshot(self, snapshot: Mapping[str, object]) -> None:
        """Restore a persisted MNN snapshot before processing the next cycle."""
        restored = MNN.from_snapshot(snapshot)
        missing = set(self.input_features) - restored.units.keys()
        if missing:
            raise ValueError(f"snapshot is missing configured input units: {sorted(missing)}")
        self.network = restored

    def analyze(
        self,
        *,
        observation: Artifact,
        workspace: Artifact,
        retrieval: Artifact,
        goal: Artifact,
        request: Artifact,
    ) -> Mapping[str, object]:
        result = dict(self.base_engine.analyze(
            observation=observation,
            workspace=workspace,
            retrieval=retrieval,
            goal=goal,
            request=request,
        ))
        text = _text(observation.data["content"])
        goal_text = _text(goal.data["description"])
        features = {
            "text_length": min(len(text), 1000) / 1000.0,
            "token_count": min(len(re.findall(r"[\wÀ-ÿ]+", text)), 200) / 200.0,
            "digit_count": min(sum(char.isdigit() for char in text), 100) / 100.0,
            "punctuation_count": min(sum(not char.isalnum() and not char.isspace() for char in text), 100) / 100.0,
            "goal_length": min(len(goal_text), 1000) / 1000.0,
            "memory_count": min(len(retrieval.data["memory_ids"]), 8) / 8.0,
            "source_reliability": float(observation.data.get("reliability", 1.0)),
        }
        inputs = {
            unit_id: features[feature]
            for unit_id, feature in self.input_features.items()
        }
        activations = self.network.step(inputs)
        understanding = dict(result.get("understanding", {}))
        understanding["mnn_signal"] = {
            "features": inputs,
            "activations": activations,
            "timestep": self.network.timestep,
            "interpretation": "numeric diagnostic signal; not a semantic conclusion",
            "snapshot": self.network.snapshot(),
        }
        result["understanding"] = understanding
        return result
