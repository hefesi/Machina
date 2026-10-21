'''Optional adapter exposing MNN signals inside the VirtualBrain cycle.

The adapter does not claim numeric activations are semantic reasoning. It wraps
an existing cognition engine, runs configured features through an MNN, and
stores the trace in the normal cognitive artifact.
'''
from __future__ import annotations

import re
from collections.abc import Mapping

from .components import CognitionEngine, DeterministicCognition, _text
from .contracts import Artifact
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
