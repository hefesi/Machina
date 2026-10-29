"""Add explicit lexical context cues to the integrated MNN experience loop.

Context encoding is transparent: configured tokens activate configured input
units. This is an experimental encoder, not a semantic language model.
"""
from __future__ import annotations

import math
import re
from typing import Mapping

from .mnn_agent import MNNLearningAgent
from .mnn_contextual_action_learning import MNNContextualActionLearner
from .mnn_experience import MNNExperienceCycle


class MNNIntegratedExperienceLoop:
    """Coordinate action cues and optional context cues in the same neural step."""

    def __init__(
        self,
        agent: MNNLearningAgent,
        experience_cycle: MNNExperienceCycle,
        *,
        action_inputs: Mapping[str, str],
        context_inputs: Mapping[str, str] | None = None,
        contextual_learner: MNNContextualActionLearner | None = None,
    ) -> None:
        if not isinstance(agent, MNNLearningAgent):
            raise ValueError("agent must be an MNNLearningAgent")
        if not isinstance(experience_cycle, MNNExperienceCycle):
            raise ValueError("experience_cycle must be an MNNExperienceCycle")
        if not isinstance(action_inputs, Mapping):
            raise ValueError("action_inputs must be a mapping")
        if set(action_inputs) != set(agent.learner.actions):
            raise ValueError("action_inputs must map every configured action exactly once")
        if any(not isinstance(unit, str) or not unit.strip() for unit in action_inputs.values()):
            raise ValueError("action input unit identifiers must be non-empty strings")
        if len(set(action_inputs.values())) != len(action_inputs):
            raise ValueError("each action must map to a distinct input unit")

        context_inputs = {} if context_inputs is None else context_inputs
        if not isinstance(context_inputs, Mapping):
            raise ValueError("context_inputs must be a mapping")
        normalized_context: dict[str, str] = {}
        for token, unit in context_inputs.items():
            if not isinstance(token, str) or not re.fullmatch(r"\w+", token, flags=re.UNICODE):
                raise ValueError("context input keys must be single lexical tokens")
            normalized = token.casefold()
            if normalized in normalized_context:
                raise ValueError("context tokens must be unique after case normalization")
            if not isinstance(unit, str) or not unit.strip():
                raise ValueError("context input unit identifiers must be non-empty strings")
            normalized_context[normalized] = unit
        all_units = list(action_inputs.values()) + list(normalized_context.values())
        if len(set(all_units)) != len(all_units):
            raise ValueError("action and context cues must map to distinct input units")
        missing = set(all_units) - set(experience_cycle.network.units)
        if missing:
            raise ValueError(f"input units are missing from the MNN: {sorted(missing)}")
        if (agent.pending_action is None) != (experience_cycle.pending_steps == 0):
            raise ValueError("agent pending action and neural experience state are inconsistent")
        self.agent = agent
        self.experience_cycle = experience_cycle
        self.action_inputs = dict(action_inputs)
        if contextual_learner is not None and not isinstance(contextual_learner, MNNContextualActionLearner):
            raise ValueError("contextual_learner must be an MNNContextualActionLearner or None")
        if contextual_learner is not None and tuple(contextual_learner.actions) != tuple(agent.learner.actions):
            raise ValueError("contextual learner actions must match agent actions in the same order")
        self.context_inputs = normalized_context
        self.contextual_learner = contextual_learner

    @staticmethod
    def _tokens(context: str) -> set[str]:
        return {
            token.casefold()
            for token in re.findall(r"\w+", context, flags=re.UNICODE)
            if len(token) > 1
        }

    def encode_context(self, context: str | None) -> dict[str, float]:
        """Return deterministic activations for configured context tokens."""
        if context is None:
            context = ""
        if not isinstance(context, str):
            raise ValueError("context must be a string")
        tokens = self._tokens(context)
        return {unit: float(token in tokens) for token, unit in self.context_inputs.items()}

    def decide(self, **decision_options: object) -> dict:
        """Choose an action and step the MNN with action and context cues."""
        if self.agent.pending_action is not None or self.experience_cycle.pending_steps:
            raise RuntimeError("resolve the current experience before choosing another action")
        context = decision_options.get("context")
        context_text = context if isinstance(context, str) else ""
        context_activations = self.encode_context(context_text)
        decision = self.agent.decide(**decision_options)
        action = decision["action"]
        contextual_result = None
        if self.contextual_learner is not None and context_text.strip():
            contextual_result = self.contextual_learner.recommend(context_text)
            if contextual_result.get("status") == "recommended":
                action = contextual_result["action"]
                self.agent.pending_action = action
                self.agent.pending_action_source = "contextual_learner"
                decision = {**decision, "action": action, "predicted_utility": self.agent.learner.predictions()[action], "selection_source": "contextual_learner"}
        decision["contextual_learning"] = contextual_result
        inputs = {
            unit: float(candidate == action)
            for candidate, unit in self.action_inputs.items()
        }
        inputs.update(context_activations)
        try:
            outputs = self.experience_cycle.step(inputs)
        except Exception:
            self.agent.pending_action = None
            self.agent.pending_action_source = None
            self.agent.learner._last_action = None
            raise
        active_context = [
            token for token, unit in self.context_inputs.items()
            if context_activations[unit] == 1.0
        ]
        return {
            **decision,
            "neural_outputs": outputs,
            "neural_step": self.experience_cycle.pending_steps,
            "context_cues": active_context,
            "unmapped_context_tokens": sorted(self._tokens(context_text) - set(self.context_inputs)),
        }

    def resolve(self, reward: float, *, context: str = "") -> dict:
        """Resolve action-value learning, neural plasticity, and memory."""
        if self.agent.pending_action is None or self.experience_cycle.pending_steps == 0:
            raise RuntimeError("a decision must be made before resolving its outcome")
        if isinstance(reward, bool):
            raise ValueError("reward must be a finite number")
        try:
            value = float(reward)
        except (TypeError, ValueError) as error:
            raise ValueError("reward must be a finite number") from error
        if not math.isfinite(value):
            raise ValueError("reward must be a finite number")
        if not isinstance(context, str):
            raise ValueError("context must be a string")
        action_before_resolve = self.agent.pending_action
        agent_result = self.agent.resolve(value, context=context)
        contextual_update = None
        if self.contextual_learner is not None and context.strip() and action_before_resolve is not None:
            contextual_update = self.contextual_learner.observe(context, action_before_resolve, value)
        neural_result = self.experience_cycle.resolve(value)
        return {
            "action_learning": agent_result["learning_update"],
            "contextual_learning_update": contextual_update,
            "neural_plasticity": neural_result["weight_changes"],
            "experience_id": agent_result["experience_id"],
            "experience_count": agent_result["experience_count"],
            "reward": value,
            "pending_neural_steps": neural_result["pending_steps"],
            "predictions": agent_result["predictions"],
        }

    def snapshot(self) -> dict:
        """Checkpoint both learning states; SQLite memory is stored separately."""
        return {
            "schema_version": 2,
            "action_inputs": dict(self.action_inputs),
            "context_inputs": dict(self.context_inputs),
            "contextual_learner": self.contextual_learner.snapshot() if self.contextual_learner else None,
            "agent": self.agent.snapshot(),
            "experience_cycle": self.experience_cycle.snapshot(),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping, *, memory) -> "MNNIntegratedExperienceLoop":
        """Restore a checkpoint while reconnecting the caller's durable memory."""
        if data.get("schema_version") not in (1, 2):
            raise ValueError("unsupported integrated experience-loop snapshot schema")
        agent = MNNLearningAgent.from_snapshot(data["agent"], memory)
        cycle = MNNExperienceCycle.from_snapshot(data["experience_cycle"])
        return cls(
            agent,
            cycle,
            action_inputs=data["action_inputs"],
            context_inputs=data.get("context_inputs", {}),
            contextual_learner=(MNNContextualActionLearner.from_snapshot(data["contextual_learner"]) if data.get("contextual_learner") is not None else None),
        )
