"""Online action-value estimates keyed by normalized lexical context.

This learner uses exact normalized token sets as context keys. It is deliberately
transparent and does not claim semantic similarity or causal understanding.
"""
from __future__ import annotations

import math
import re
from typing import Mapping, Iterable


class MNNContextualActionLearner:
    """Maintain independent action-value estimates for each observed context."""

    def __init__(
        self,
        actions: Iterable[str],
        *,
        learning_rate: float = 0.25,
        min_samples_per_action: int = 2,
        min_reward_margin: float = 0.1,
    ) -> None:
        names = tuple(actions)
        if len(names) < 2 or any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("at least two non-empty action names are required")
        if len(set(names)) != len(names):
            raise ValueError("action names must be unique")
        if (
            isinstance(learning_rate, bool)
            or not isinstance(learning_rate, (int, float))
            or not math.isfinite(learning_rate)
            or not 0 < learning_rate <= 1
        ):
            raise ValueError("learning_rate must be finite and in (0, 1]")
        if (
            isinstance(min_samples_per_action, bool)
            or not isinstance(min_samples_per_action, int)
            or min_samples_per_action < 1
        ):
            raise ValueError("min_samples_per_action must be a positive integer")
        if (
            isinstance(min_reward_margin, bool)
            or not isinstance(min_reward_margin, (int, float))
            or not math.isfinite(min_reward_margin)
            or min_reward_margin < 0
        ):
            raise ValueError("min_reward_margin must be finite and non-negative")

        self.actions = names
        self.learning_rate = float(learning_rate)
        self.min_samples_per_action = min_samples_per_action
        self.min_reward_margin = float(min_reward_margin)
        self._values: dict[str, dict[str, float]] = {}
        self._counts: dict[str, dict[str, int]] = {}
        self._contexts: dict[str, str] = {}

    @staticmethod
    def _context_key(context: str) -> tuple[str, str]:
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        tokens = sorted({
            token.casefold()
            for token in re.findall(r"\w+", context, flags=re.UNICODE)
            if len(token) > 1
        })
        if not tokens:
            raise ValueError("context must contain at least one searchable token")
        key = " ".join(tokens)
        return key, " ".join(tokens)

    def observe(self, context: str, action: str, reward: float) -> dict:
        """Update one context/action estimate using an exponential moving average."""
        key, display_context = self._context_key(context)
        if action not in self.actions:
            raise ValueError("action must be one of the configured actions")
        if isinstance(reward, bool):
            raise ValueError("reward must be a finite number")
        try:
            value = float(reward)
        except (TypeError, ValueError) as error:
            raise ValueError("reward must be a finite number") from error
        if not math.isfinite(value):
            raise ValueError("reward must be a finite number")

        values = self._values.setdefault(key, {name: 0.0 for name in self.actions})
        counts = self._counts.setdefault(key, {name: 0 for name in self.actions})
        previous = values[action]
        updated = value if counts[action] == 0 else (
            previous + self.learning_rate * (value - previous)
        )
        values[action] = updated
        counts[action] += 1
        self._contexts[key] = display_context
        return {
            "context_key": key,
            "action": action,
            "reward": value,
            "value_before": previous,
            "value_after": updated,
            "observations": counts[action],
        }

    def recommend(self, context: str) -> dict:
        """Recommend an action only when all actions have sufficient evidence."""
        key, display_context = self._context_key(context)
        counts = self._counts.get(key, {name: 0 for name in self.actions})
        values = self._values.get(key, {name: 0.0 for name in self.actions})
        insufficient = [
            action for action in self.actions
            if counts[action] < self.min_samples_per_action
        ]
        if insufficient:
            return {
                "status": "abstain",
                "reason": "insufficient_contextual_observations",
                "context": display_context,
                "sample_counts": dict(counts),
                "missing_actions": insufficient,
            }
        ranked = sorted(self.actions, key=lambda action: (-values[action], self.actions.index(action)))
        best, runner_up = ranked[:2]
        margin = values[best] - values[runner_up]
        if margin < self.min_reward_margin:
            return {
                "status": "abstain",
                "reason": "contextual_values_too_close",
                "context": display_context,
                "estimated_values": dict(values),
                "sample_counts": dict(counts),
                "value_margin": margin,
            }
        return {
            "status": "recommended",
            "reason": "minimum_contextual_evidence_satisfied",
            "action": best,
            "context": display_context,
            "estimated_values": dict(values),
            "sample_counts": dict(counts),
            "value_margin": margin,
            "interpretation": (
                "Online reward estimates for an exact normalized token-set context; "
                "this is lexical partitioning, not semantic understanding."
            ),
        }

    def snapshot(self) -> dict:
        """Return JSON-compatible state for checkpointing."""
        return {
            "schema_version": 1,
            "actions": list(self.actions),
            "learning_rate": self.learning_rate,
            "min_samples_per_action": self.min_samples_per_action,
            "min_reward_margin": self.min_reward_margin,
            "values": {key: dict(values) for key, values in self._values.items()},
            "counts": {key: dict(counts) for key, counts in self._counts.items()},
            "contexts": dict(self._contexts),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNContextualActionLearner":
        if not isinstance(data, Mapping) or data.get("schema_version") != 1:
            raise ValueError("unsupported contextual action-learner snapshot schema")
        learner = cls(
            data["actions"],
            learning_rate=data["learning_rate"],
            min_samples_per_action=data["min_samples_per_action"],
            min_reward_margin=data["min_reward_margin"],
        )
        values = data["values"]
        counts = data["counts"]
        contexts = data["contexts"]
        if not isinstance(values, Mapping) or not isinstance(counts, Mapping) or not isinstance(contexts, Mapping):
            raise ValueError("snapshot values, counts, and contexts must be mappings")
        if set(values) != set(counts) or set(values) != set(contexts):
            raise ValueError("snapshot context keys must match across values, counts, and contexts")
        restored_values: dict[str, dict[str, float]] = {}
        restored_counts: dict[str, dict[str, int]] = {}
        restored_contexts: dict[str, str] = {}
        for key, per_action in values.items():
            if not isinstance(key, str) or not key or not isinstance(per_action, Mapping) or set(per_action) != set(learner.actions):
                raise ValueError("snapshot values must contain every action for each context")
            per_counts = counts[key]
            if not isinstance(per_counts, Mapping) or set(per_counts) != set(learner.actions):
                raise ValueError("snapshot counts must contain every action for each context")
            normalized_values: dict[str, float] = {}
            normalized_counts: dict[str, int] = {}
            for action in learner.actions:
                value = per_action[action]
                count = per_counts[action]
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ValueError("snapshot action values must be finite numbers")
                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    raise ValueError("snapshot observation counts must be non-negative integers")
                normalized_values[action] = float(value)
                normalized_counts[action] = count
            context = contexts[key]
            if not isinstance(context, str) or not context:
                raise ValueError("snapshot contexts must be non-empty strings")
            normalized_key, _ = learner._context_key(context)
            if normalized_key != key:
                raise ValueError("snapshot context does not match its normalized key")
            restored_values[key] = normalized_values
            restored_counts[key] = normalized_counts
            restored_contexts[key] = context
        learner._values = restored_values
        learner._counts = restored_counts
        learner._contexts = restored_contexts
        return learner
