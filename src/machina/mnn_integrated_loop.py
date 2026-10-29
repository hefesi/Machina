"""Connect action selection, neural activity, delayed reward, and durable memory.

This coordinator joins existing components without conflating their learning
signals: the action learner updates action values, while the experience cycle
applies reward credit to eligible MNN connections. FragmentMemory is shared by
the agent and remains the durable archive; the neural/action checkpoint is
exported separately by snapshot().
"""
from __future__ import annotations

import math
from typing import Mapping

from .mnn_agent import MNNLearningAgent
from .mnn_experience import MNNExperienceCycle


class MNNIntegratedExperienceLoop:
    """Coordinate one action, its neural cue, delayed reward, and memory record.

    `action_inputs` maps every action name to a distinct input-unit identifier
    already present in the experience cycle's network. The chosen cue receives
    1.0 and other action cues receive 0.0 for each decision step.
    """

    def __init__(
        self,
        agent: MNNLearningAgent,
        experience_cycle: MNNExperienceCycle,
        *,
        action_inputs: Mapping[str, str],
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
        missing = set(action_inputs.values()) - set(experience_cycle.network.units)
        if missing:
            raise ValueError(f"action input units are missing from the MNN: {sorted(missing)}")
        if (agent.pending_action is None) != (experience_cycle.pending_steps == 0):
            raise ValueError("agent pending action and neural experience state are inconsistent")
        self.agent = agent
        self.experience_cycle = experience_cycle
        self.action_inputs = dict(action_inputs)

    def decide(self, **decision_options: object) -> dict:
        """Choose an action and immediately record its neural cue activity."""
        if self.agent.pending_action is not None or self.experience_cycle.pending_steps:
            raise RuntimeError("resolve the current experience before choosing another action")
        decision = self.agent.decide(**decision_options)
        action = decision["action"]
        inputs = {unit: float(candidate == action) for candidate, unit in self.action_inputs.items()}
        try:
            outputs = self.experience_cycle.step(inputs)
        except Exception:
            # Keep the agent from being stranded with a pending action if the
            # neural step fails before the experience has begun.
            self.agent.pending_action = None
            self.agent.pending_action_source = None
            self.agent.learner._last_action = None
            raise
        return {**decision, "neural_outputs": outputs, "neural_step": self.experience_cycle.pending_steps}

    def resolve(self, reward: float, *, context: str = "") -> dict:
        """Resolve both learning paths and persist the agent's outcome record."""
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

        # The agent validates, updates its action learner, and commits the
        # auditable outcome to FragmentMemory. The cycle then applies the same
        # reward to its eligibility traces.
        agent_result = self.agent.resolve(value, context=context)
        neural_result = self.experience_cycle.resolve(value)
        return {
            "action_learning": agent_result["learning_update"],
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
            "schema_version": 1,
            "action_inputs": dict(self.action_inputs),
            "agent": self.agent.snapshot(),
            "experience_cycle": self.experience_cycle.snapshot(),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping, *, memory) -> "MNNIntegratedExperienceLoop":
        """Restore a checkpoint while reconnecting the caller's durable memory."""
        if data.get("schema_version") != 1:
            raise ValueError("unsupported integrated experience-loop snapshot schema")
        agent = MNNLearningAgent.from_snapshot(data["agent"], memory)
        cycle = MNNExperienceCycle.from_snapshot(data["experience_cycle"])
        return cls(agent, cycle, action_inputs=data["action_inputs"])
