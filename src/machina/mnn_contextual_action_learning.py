"""Online action-value estimates keyed by normalized lexical context.

This learner stores normalized lexical contexts and can optionally transfer
weighted evidence between similar token sets. Similarity is lexical Jaccard, not
semantic similarity or causal understanding.
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
        min_context_similarity: float = 0.5,
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

        if (
            isinstance(min_context_similarity, bool)
            or not isinstance(min_context_similarity, (int, float))
            or not math.isfinite(min_context_similarity)
            or not 0 < min_context_similarity <= 1
        ):
            raise ValueError("min_context_similarity must be finite and in (0, 1]")

        self.actions = names
        self.learning_rate = float(learning_rate)
        self.min_samples_per_action = min_samples_per_action
        self.min_reward_margin = float(min_reward_margin)
        self.min_context_similarity = float(min_context_similarity)
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

    @staticmethod
    def _similarity(left_key: str, right_key: str) -> float:
        left, right = set(left_key.split()), set(right_key.split())
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    def recommend(self, context: str) -> dict:
        """Recommend using exact evidence plus cautiously weighted lexical neighbors."""
        key, display_context = self._context_key(context)
        values = {action: 0.0 for action in self.actions}
        evidence = {action: 0.0 for action in self.actions}
        contributing_contexts = []
        for observed_key, observed_values in self._values.items():
            similarity = self._similarity(key, observed_key)
            if similarity < self.min_context_similarity:
                continue
            observed_counts = self._counts[observed_key]
            contributing_contexts.append({
                "context": self._contexts[observed_key],
                "similarity": similarity,
            })
            for action in self.actions:
                weighted_count = similarity * observed_counts[action]
                values[action] += observed_values[action] * weighted_count
                evidence[action] += weighted_count

        estimates = {
            action: values[action] / evidence[action] if evidence[action] else 0.0
            for action in self.actions
        }
        insufficient = [
            action for action in self.actions
            if evidence[action] < self.min_samples_per_action
        ]
        common = {
            "context": display_context,
            "estimated_values": estimates,
            "effective_sample_counts": evidence,
            "contributing_contexts": contributing_contexts,
            "min_context_similarity": self.min_context_similarity,
        }
        if insufficient:
            return {
                "status": "abstain",
                "reason": "insufficient_similar_context_evidence",
                **common,
                "missing_actions": insufficient,
            }
        ranked = sorted(self.actions, key=lambda action: (-estimates[action], self.actions.index(action)))
        best, runner_up = ranked[:2]
        margin = estimates[best] - estimates[runner_up]
        if margin < self.min_reward_margin:
            return {
                "status": "abstain",
                "reason": "contextual_values_too_close",
                **common,
                "sample_counts": {
                    action: self._counts.get(key, {}).get(action, 0)
                    for action in self.actions
                },
                "value_margin": margin,
            }
        return {
            "status": "recommended",
            "reason": "similar_context_evidence_satisfied",
            "action": best,
            **common,
            "sample_counts": {
                action: self._counts.get(key, {}).get(action, 0)
                for action in self.actions
            },
            "value_margin": margin,
            "interpretation": (
                "Values combine observed rewards from token sets whose Jaccard "
                "similarity meets the threshold. This is lexical transfer, not "
                "semantic understanding; review contributing contexts."
            ),
        }

    def snapshot(self) -> dict:
        """Return JSON-compatible state for checkpointing."""
        return {
            "schema_version": 2,
            "actions": list(self.actions),
            "learning_rate": self.learning_rate,
            "min_samples_per_action": self.min_samples_per_action,
            "min_reward_margin": self.min_reward_margin,
            "min_context_similarity": self.min_context_similarity,
            "values": {key: dict(values) for key, values in self._values.items()},
            "counts": {key: dict(counts) for key, counts in self._counts.items()},
            "contexts": dict(self._contexts),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNContextualActionLearner":
        if not isinstance(data, Mapping) or data.get("schema_version") not in (1, 2):
            raise ValueError("unsupported contextual action-learner snapshot schema")
        learner = cls(
            data["actions"],
            learning_rate=data["learning_rate"],
            min_samples_per_action=data["min_samples_per_action"],
            min_reward_margin=data["min_reward_margin"],
            min_context_similarity=data.get("min_context_similarity", 1.0 if data.get("schema_version") == 1 else 0.5),
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
