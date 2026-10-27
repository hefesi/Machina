"""A minimal action -> outcome -> persistent experience loop for Machina.

The agent coordinates a bounded action-value learner with FragmentMemory.
Memory is an auditable record of outcomes; it is not treated as semantic
understanding and does not silently rewrite the policy.
"""
from __future__ import annotations

import math
from typing import Mapping

from .fragment_memory import FragmentMemory, MemoryFragment
from .mnn_action_learning import MNNActionLearner


class MNNLearningAgent:
    """Coordinate one pending action, outcome-based learning, and memory."""

    def __init__(
        self,
        learner: MNNActionLearner,
        memory: FragmentMemory,
        *,
        agent_id: str = "machina",
    ) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        self.learner = learner
        self.memory = memory
        self.agent_id = agent_id.strip()
        self.pending_action: str | None = None
        self.experience_count = 0

    def decide(self) -> dict:
        """Choose one action and return its predicted utility."""
        if self.pending_action is not None:
            raise RuntimeError("resolve the pending action before choosing another")
        action = self.learner.choose()
        self.pending_action = action
        return {
            "action": action,
            "predicted_utility": self.learner.predictions()[action],
            "decision": self.learner.decisions,
        }

    def resolve(self, reward: float, *, context: str = "") -> dict:
        """Learn from the pending action and archive its observed outcome."""
        if self.pending_action is None:
            raise RuntimeError("cannot resolve an outcome without a pending action")
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

        action = self.pending_action
        update = self.learner.observe(value, action=action)
        fragment = self.memory.add(
            f"Action '{action}' received reward {value:g}."
            + (f" Context: {context.strip()}" if context.strip() else ""),
            kind="action-outcome",
            source_uri=f"machina://{self.agent_id}/experience/{self.experience_count + 1}",
            importance=min(1.0, 0.5 + abs(value) / 10.0),
            confidence=1.0,
            tags=("action-learning", action, "positive-outcome" if value > 0 else "non-positive-outcome"),
            metadata={
                "agent_id": self.agent_id,
                "action": action,
                "reward": value,
                "prediction_error": update["prediction_error"],
                "decision": self.learner.decisions,
                "context": context.strip(),
            },
        )
        self.experience_count += 1
        self.pending_action = None
        return {
            "learning_update": update,
            "experience_id": fragment.id,
            "experience_count": self.experience_count,
            "predictions": self.learner.predictions(),
        }

    def recall(self, query: str, *, limit: int = 5) -> list[MemoryFragment]:
        """Recall explicit experience records using FragmentMemory's lexical search."""
        return self.memory.recall(query, limit=limit)

    def snapshot(self) -> dict:
        """Capture learner and in-flight action state; SQLite is persisted separately."""
        return {
            "schema_version": 1,
            "agent_id": self.agent_id,
            "learner": self.learner.snapshot(),
            "pending_action": self.pending_action,
            "experience_count": self.experience_count,
        }

    @classmethod
    def from_snapshot(
        cls, data: Mapping, memory: FragmentMemory
    ) -> "MNNLearningAgent":
        if data.get("schema_version") != 1:
            raise ValueError("unsupported MNN learning-agent snapshot schema")
        learner = MNNActionLearner.from_snapshot(data["learner"])
        agent = cls(learner, memory, agent_id=data["agent_id"])
        pending = data.get("pending_action")
        if pending is not None and pending not in learner.actions:
            raise ValueError("pending_action is not a configured action")
        count = data.get("experience_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("experience_count must be a non-negative integer")
        if pending is not None and learner._last_action != pending:
            raise ValueError("pending_action does not match the learner's pending choice")
        agent.pending_action = pending
        agent.experience_count = count
        return agent
