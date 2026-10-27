"""A minimal action -> outcome -> persistent experience loop for Machina.

The agent coordinates a bounded action-value learner with FragmentMemory.
Memory is an auditable record of outcomes; it is not treated as semantic
understanding and does not silently rewrite the policy.
"""
from __future__ import annotations

import math
import re
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

    def decide(self, *, context: str | None = None, use_memory: bool = False) -> dict:
        """Choose an action, optionally using an explicit contextual memory recommendation.

        The learner always advances its decision counter and provides a fallback.
        When use_memory=True, a usable memory recommendation overrides that
        fallback for this decision only; learning still occurs in resolve().
        """
        if self.pending_action is not None:
            raise RuntimeError("resolve the pending action before choosing another")
        if not isinstance(use_memory, bool):
            raise ValueError("use_memory must be boolean")
        if context is not None and not isinstance(context, str):
            raise ValueError("context must be a string")
        if use_memory and (context is None or not context.strip()):
            raise ValueError("a non-empty context is required when use_memory=True")

        fallback = self.learner.choose()
        recommendation = (
            self.recommend_from_memory(context)
            if use_memory and context is not None
            else None
        )
        action = recommendation["action"] if recommendation else fallback
        self.pending_action = action
        return {
            "action": action,
            "predicted_utility": self.learner.predictions()[action],
            "decision": self.learner.decisions,
            "context": context,
            "selection_source": "memory" if recommendation else "learner",
            "memory_recommendation": recommendation,
            "fallback_action": fallback,
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

    def recommend_from_memory(self, context: str, *, limit: int = 20) -> dict | None:
        """Recommend an action from context-matching archived outcomes.

        This is an explicit, explainable memory-based recommendation; it does
        not modify the learner or choose an action automatically. Only recorded
        action-outcome fragments with a known action and overlapping context
        tokens participate. Rewards are averaged per action, weighted by
        context-token overlap. Returns None when no usable context evidence
        exists, so callers can fall back to the ordinary learner.
        """
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")

        def tokens(value: str) -> set[str]:
            return {
                token.casefold()
                for token in re.findall(r"\w+", value, flags=re.UNICODE)
                if len(token) > 1
            }

        query_tokens = tokens(context)
        if not query_tokens:
            return None
        fragments = self.memory.recall(context, limit=limit)
        totals: dict[str, float] = {}
        weights: dict[str, float] = {}
        evidence: dict[str, list[str]] = {}
        for fragment in fragments:
            if fragment.kind != "action-outcome":
                continue
            metadata = fragment.metadata
            action = metadata.get("action")
            stored_context = metadata.get("context", "")
            if action not in self.learner.actions or not isinstance(stored_context, str):
                continue
            overlap = len(query_tokens & tokens(stored_context)) / len(query_tokens)
            if overlap <= 0:
                continue
            reward = metadata.get("reward")
            if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
                continue
            weight = overlap * max(0.01, fragment.confidence)
            totals[action] = totals.get(action, 0.0) + float(reward) * weight
            weights[action] = weights.get(action, 0.0) + weight
            evidence.setdefault(action, []).append(fragment.id)

        if not weights:
            return None
        estimates = {action: totals[action] / weights[action] for action in weights}
        # Stable tie-breaking follows the learner's configured action order.
        action = max(
            estimates,
            key=lambda name: (estimates[name], -self.learner.actions.index(name)),
        )
        return {
            "action": action,
            "estimated_reward": estimates[action],
            "context": context.strip(),
            "evidence_ids": evidence[action],
            "estimates_by_action": estimates,
            "method": "lexical-context-overlap-weighted-reward-mean",
        }

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
