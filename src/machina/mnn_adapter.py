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
from .contracts import Artifact
from .mnn import MNN
from .mnn_experience import MNNExperienceCycle


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
        delayed_reward: bool = False,
        max_pending_steps: int | None = None,
    ) -> None:
        if not input_features:
            raise ValueError("input_features must map at least one unit to a feature")
        unknown_features = set(input_features.values()) - _SUPPORTED_FEATURES
        if unknown_features:
            raise ValueError(f"unsupported MNN features: {sorted(unknown_features)}")
        unknown_units = set(input_features) - network.units.keys()
        if unknown_units:
            raise ValueError(f"unknown MNN input units: {sorted(unknown_units)}")
        if not isinstance(delayed_reward, bool):
            raise ValueError("delayed_reward must be boolean")
        if max_pending_steps is not None and not delayed_reward:
            raise ValueError("max_pending_steps requires delayed_reward=True")
        self.network = network
        self.input_features = dict(input_features)
        self.base_engine = base_engine or DeterministicCognition()
        self.learning_rate = float(learning_rate)
        if self.learning_rate < 0 or not math.isfinite(self.learning_rate):
            raise ValueError("learning_rate must be finite and non-negative")
        self.delayed_reward = delayed_reward
        self.cycle = (
            MNNExperienceCycle(
                network,
                learning_rate=self.learning_rate,
                max_pending_steps=max_pending_steps,
            )
            if delayed_reward
            else None
        )
        self.max_pending_steps = (
            self.cycle.max_pending_steps if self.cycle is not None else None
        )

    def propose_evaluated_outcome(
        self, *, evaluation: Artifact, validation: Artifact
    ) -> Mapping[str, object]:
        """Compute a bounded plasticity proposal without mutating live state.

        The orchestrator first persists this proposal in the append-only journal,
        then commits the saved snapshot back into the adapter. This ordering
        avoids changing in-memory weights if the journal append fails.
        """
        succeeded = bool(evaluation.data["success"])
        reward = 1.0 if succeeded else -1.0
        if self.cycle is not None:
            if self.cycle.pending_steps == 0:
                raise RuntimeError(
                    "cannot resolve an MNN outcome without a pending experience"
                )
            candidate = MNNExperienceCycle.from_snapshot(self.cycle.snapshot())
            resolution = candidate.resolve(reward)
            result = {
                "success": succeeded,
                "reward": reward,
                "validation_status": validation.data["status"],
                "weight_deltas": resolution["weight_changes"],
                "snapshot": candidate.network.snapshot(),
                "experience_snapshot": candidate.snapshot(),
                "pending_steps": resolution["pending_steps"],
                "credit_assignment": "delayed eligibility",
            }
            return result

        candidate = MNN.from_snapshot(self.network.snapshot())
        weight_deltas = candidate.apply_hebbian(
            learning_rate=self.learning_rate,
            reward=reward,
        )
        return {
            "success": succeeded,
            "reward": reward,
            "validation_status": validation.data["status"],
            "weight_deltas": weight_deltas,
            "snapshot": candidate.snapshot(),
            "credit_assignment": "immediate hebbian",
        }

    def abort_pending_experience(self) -> dict:
        """Discard an orphaned delayed experience without changing weights."""
        if self.cycle is None:
            raise RuntimeError("delayed reward is not enabled")
        return self.cycle.abort()

    def _validate_network(self, network: MNN) -> None:
        missing = set(self.input_features) - network.units.keys()
        if missing:
            raise ValueError(f"snapshot is missing configured input units: {sorted(missing)}")

    @staticmethod
    def _is_experience_snapshot(snapshot: Mapping[str, object]) -> bool:
        return "network" in snapshot and "modulator" in snapshot

    def restore_from_snapshot(self, snapshot: Mapping[str, object]) -> None:
        """Restore network state or a full in-flight experience snapshot."""
        if not isinstance(snapshot, Mapping):
            raise ValueError("snapshot must be a mapping")
        if self._is_experience_snapshot(snapshot):
            cycle = MNNExperienceCycle.from_snapshot(snapshot)
            self._validate_network(cycle.network)
            if self.delayed_reward:
                limits = [
                    limit
                    for limit in (self.max_pending_steps, cycle.max_pending_steps)
                    if limit is not None
                ]
                if limits:
                    effective_limit = min(limits)
                    if cycle.pending_steps > effective_limit:
                        raise ValueError(
                            "pending_steps cannot exceed the configured max_pending_steps"
                        )
                    cycle.max_pending_steps = effective_limit
                self.max_pending_steps = cycle.max_pending_steps
            self.network = cycle.network
            self.cycle = cycle if self.delayed_reward else None
            return
        restored = MNN.from_snapshot(snapshot)
        self._validate_network(restored)
        self.network = restored
        if self.delayed_reward:
            self.cycle = MNNExperienceCycle(
                restored,
                learning_rate=self.learning_rate,
                max_pending_steps=self.max_pending_steps,
            )

    def restore_from_outcome(self, change: Mapping[str, object]) -> None:
        """Restore the exact post-outcome state persisted for this cycle."""
        if not isinstance(change, Mapping):
            raise ValueError("outcome change must be a mapping")
        experience_snapshot = change.get("experience_snapshot")
        if self.delayed_reward and isinstance(experience_snapshot, Mapping):
            self.restore_from_snapshot(experience_snapshot)
            return
        snapshot = change.get("snapshot")
        if not isinstance(snapshot, Mapping):
            raise ValueError("outcome change must include a snapshot")
        self.restore_from_snapshot(snapshot)

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
        if self.cycle is not None:
            activations = self.cycle.step(inputs)
            experience_snapshot = self.cycle.snapshot()
            credit_assignment = "delayed eligibility"
        else:
            activations = self.network.step(inputs)
            experience_snapshot = None
            credit_assignment = "immediate hebbian"
        signal = {
            "features": inputs,
            "activations": activations,
            "timestep": self.network.timestep,
            "interpretation": "numeric diagnostic signal; not a semantic conclusion",
            "snapshot": self.network.snapshot(),
            "credit_assignment": credit_assignment,
        }
        if experience_snapshot is not None:
            signal["experience_snapshot"] = experience_snapshot
            signal["pending_steps"] = self.cycle.pending_steps
        understanding = dict(result.get("understanding", {}))
        understanding["mnn_signal"] = signal
        result["understanding"] = understanding
        return result
