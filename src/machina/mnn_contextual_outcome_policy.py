"""Conservative action recommendations from archived contextual outcomes.

This module estimates observed reward by explicit lexical context and action.
It is an empirical association, not causal inference or semantic understanding.
"""
from __future__ import annotations

import math
import re
from typing import Iterable

from .fragment_memory import FragmentMemory


class MNNContextualOutcomePolicy:
    """Recommend only when every configured action has enough comparable evidence.

    The policy reads the complete persistent archive, not only the bounded active
    memory view. It never mutates memory or learner state. Missing evidence,
    weak context overlap, and small reward margins lead to abstention.
    """

    def __init__(
        self,
        memory: FragmentMemory,
        actions: Iterable[str],
        *,
        min_samples_per_action: int = 2,
        min_reward_margin: float = 0.1,
        min_context_overlap: float = 0.6,
        recency_half_life_decisions: float | None = None,
    ) -> None:
        if not isinstance(memory, FragmentMemory):
            raise ValueError("memory must be a FragmentMemory")
        names = tuple(actions)
        if len(names) < 2 or any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError("at least two non-empty action names are required")
        if len(set(names)) != len(names):
            raise ValueError("action names must be unique")
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
            isinstance(min_context_overlap, bool)
            or not isinstance(min_context_overlap, (int, float))
            or not math.isfinite(min_context_overlap)
            or not 0 < min_context_overlap <= 1
        ):
            raise ValueError("min_context_overlap must be in (0, 1]")
        self.memory = memory
        self.actions = names
        self.min_samples_per_action = min_samples_per_action
        self.min_reward_margin = float(min_reward_margin)
        if recency_half_life_decisions is not None and (
            isinstance(recency_half_life_decisions, bool)
            or not isinstance(recency_half_life_decisions, (int, float))
            or not math.isfinite(recency_half_life_decisions)
            or recency_half_life_decisions <= 0
        ):
            raise ValueError("recency_half_life_decisions must be finite and positive or None")
        self.min_context_overlap = float(min_context_overlap)
        self.recency_half_life_decisions = (
            None if recency_half_life_decisions is None
            else float(recency_half_life_decisions)
        )

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {
            token.casefold()
            for token in re.findall(r"\w+", value, flags=re.UNICODE)
            if len(token) > 1
        }

    def recommend(self, context: str) -> dict:
        """Return an evidence-backed recommendation or an explicit abstention."""
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        query_tokens = self._tokens(context)
        if not query_tokens:
            return self._abstain(context, "context_has_no_searchable_tokens")

        archive = self.memory.archive()
        # Decision counters make recency deterministic and independent of wall-clock
        # timestamps. Legacy fragments without a valid counter remain usable at
        # full temporal weight rather than being silently discarded.
        decision_indices = [
            fragment.metadata.get("decision")
            for fragment in archive
            if fragment.kind == "action-outcome"
            and isinstance(fragment.metadata.get("decision"), int)
            and not isinstance(fragment.metadata.get("decision"), bool)
            and fragment.metadata.get("decision") >= 0
        ]
        latest_decision = max(decision_indices, default=None)
        samples: dict[str, list[tuple[float, float, str]]] = {
            action: [] for action in self.actions
        }
        for fragment in archive:
            if fragment.kind != "action-outcome":
                continue
            metadata = fragment.metadata
            action = metadata.get("action")
            stored_context = metadata.get("context")
            reward = metadata.get("reward")
            if not isinstance(action, str) or action not in samples or not isinstance(stored_context, str) or not stored_context.strip():
                continue
            if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
                continue
            stored_tokens = self._tokens(stored_context)
            if not stored_tokens:
                continue
            overlap = len(query_tokens & stored_tokens) / len(query_tokens)
            if overlap < self.min_context_overlap:
                continue
            confidence = fragment.confidence
            weight = overlap * max(0.01, confidence)
            decision_index = metadata.get("decision")
            if (
                self.recency_half_life_decisions is not None
                and latest_decision is not None
                and isinstance(decision_index, int)
                and not isinstance(decision_index, bool)
                and decision_index >= 0
            ):
                age = max(0, latest_decision - decision_index)
                weight *= math.exp(
                    -math.log(2.0) * age / self.recency_half_life_decisions
                )
            samples[action].append((float(reward), weight, fragment.id))

        counts = {action: len(samples[action]) for action in self.actions}
        evidence_ids = {action: [item[2] for item in samples[action]] for action in self.actions}
        insufficient = [
            action for action in self.actions
            if counts[action] < self.min_samples_per_action
        ]
        if insufficient:
            return self._abstain(
                context,
                "insufficient_comparable_evidence",
                sample_counts=counts,
                evidence_ids=evidence_ids,
                missing_actions=insufficient,
            )

        estimates = {
            action: sum(reward * weight for reward, weight, _ in samples[action])
            / sum(weight for _, weight, _ in samples[action])
            for action in self.actions
        }
        ranked = sorted(
            self.actions,
            key=lambda action: (-estimates[action], self.actions.index(action)),
        )
        best, runner_up = ranked[:2]
        margin = estimates[best] - estimates[runner_up]
        if margin < self.min_reward_margin:
            return self._abstain(
                context,
                "reward_estimates_too_close",
                sample_counts=counts,
                evidence_ids=evidence_ids,
                estimated_rewards=estimates,
                reward_margin=margin,
            )
        return {
            "status": "recommended",
            "reason": "minimum_evidence_and_reward_margin_satisfied",
            "action": best,
            "context": context.strip(),
            "estimated_rewards": estimates,
            "estimated_reward": estimates[best],
            "reward_margin": margin,
            "sample_counts": counts,
            "evidence_ids": evidence_ids,
            "minimum_samples_per_action": self.min_samples_per_action,
            "minimum_reward_margin": self.min_reward_margin,
            "minimum_context_overlap": self.min_context_overlap,
            "recency_half_life_decisions": self.recency_half_life_decisions,
            "latest_decision_index": latest_decision,
            "interpretation": (
                "Confidence- and lexical-overlap-weighted recorded rewards; optionally "
                "discounted exponentially by decision age. Observational association, "
                "not a causal guarantee."
            ),
        }

    @staticmethod
    def _abstain(context: str, reason: str, **details: object) -> dict:
        return {
            "status": "abstain",
            "reason": reason,
            "context": context.strip(),
            **details,
        }
