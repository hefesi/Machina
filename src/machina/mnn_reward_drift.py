"""Conservative detection of contextual reward shifts in archived outcomes.

This detects changes in observed reward distributions; it does not identify their
cause or prove that the environment itself changed.
"""
from __future__ import annotations

import math
import re

from .fragment_memory import FragmentMemory


class MNNRewardDriftDetector:
    """Compare adjacent decision windows for meaningful reward shifts.

    Detection is abstention-friendly: it requires enough matching outcomes for
    the same action in both windows and a configurable minimum mean-reward shift.
    Historical fragments are read-only and remain in the archive.
    """

    def __init__(
        self,
        memory: FragmentMemory,
        *,
        decisions_per_window: int = 5,
        min_samples_per_action_window: int = 2,
        min_reward_shift: float = 0.3,
        min_context_overlap: float = 0.6,
    ) -> None:
        if not isinstance(memory, FragmentMemory):
            raise ValueError("memory must be a FragmentMemory")
        if isinstance(decisions_per_window, bool) or not isinstance(decisions_per_window, int) or decisions_per_window < 2:
            raise ValueError("decisions_per_window must be an integer >= 2")
        if isinstance(min_samples_per_action_window, bool) or not isinstance(min_samples_per_action_window, int) or min_samples_per_action_window < 1:
            raise ValueError("min_samples_per_action_window must be a positive integer")
        if isinstance(min_reward_shift, bool) or not isinstance(min_reward_shift, (int, float)) or not math.isfinite(min_reward_shift) or min_reward_shift <= 0:
            raise ValueError("min_reward_shift must be finite and positive")
        if isinstance(min_context_overlap, bool) or not isinstance(min_context_overlap, (int, float)) or not math.isfinite(min_context_overlap) or not 0 < min_context_overlap <= 1:
            raise ValueError("min_context_overlap must be in (0, 1]")
        self.memory = memory
        self.decisions_per_window = decisions_per_window
        self.min_samples_per_action_window = min_samples_per_action_window
        self.min_reward_shift = float(min_reward_shift)
        self.min_context_overlap = float(min_context_overlap)

    @staticmethod
    def _tokens(value: str) -> set[str]:
        return {
            token.casefold()
            for token in re.findall(r"\\w+", value, flags=re.UNICODE)
            if len(token) > 1
        }

    def detect(self, context: str) -> dict:
        """Return detected, stable, or abstain with per-action evidence."""
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        query_tokens = self._tokens(context)
        if not query_tokens:
            return self._result("abstain", "context_has_no_searchable_tokens", context)

        records = []
        for fragment in self.memory.archive():
            if fragment.kind != "action-outcome":
                continue
            metadata = fragment.metadata
            decision = metadata.get("decision")
            action = metadata.get("action")
            reward = metadata.get("reward")
            stored_context = metadata.get("context")
            if (
                isinstance(decision, bool) or not isinstance(decision, int) or decision < 0
                or not isinstance(action, str) or not action.strip()
                or isinstance(reward, bool) or not isinstance(reward, (int, float))
                or not math.isfinite(reward)
                or not isinstance(stored_context, str) or not stored_context.strip()
            ):
                continue
            stored_tokens = self._tokens(stored_context)
            if not stored_tokens:
                continue
            overlap = len(query_tokens & stored_tokens) / len(query_tokens)
            if overlap < self.min_context_overlap:
                continue
            records.append({
                "decision": decision, "action": action, "reward": float(reward),
                "weight": overlap * max(0.01, fragment.confidence),
                "id": fragment.id,
            })

        decision_ids = sorted({record["decision"] for record in records})
        window_size = self.decisions_per_window
        if len(decision_ids) < window_size * 2:
            return self._result(
                "abstain", "insufficient_decision_history", context,
                available_decisions=len(decision_ids),
                required_decisions=window_size * 2,
            )
        previous_ids = set(decision_ids[-2 * window_size:-window_size])
        recent_ids = set(decision_ids[-window_size:])
        previous = [record for record in records if record["decision"] in previous_ids]
        recent = [record for record in records if record["decision"] in recent_ids]
        actions = sorted({record["action"] for record in previous + recent})
        comparisons = {}
        shifted = []
        for action in actions:
            old = [r for r in previous if r["action"] == action]
            new = [r for r in recent if r["action"] == action]
            if len(old) < self.min_samples_per_action_window or len(new) < self.min_samples_per_action_window:
                comparisons[action] = {
                    "status": "insufficient_samples",
                    "previous_samples": len(old), "recent_samples": len(new),
                }
                continue
            old_mean = sum(r["reward"] * r["weight"] for r in old) / sum(r["weight"] for r in old)
            new_mean = sum(r["reward"] * r["weight"] for r in new) / sum(r["weight"] for r in new)
            delta = new_mean - old_mean
            is_shifted = abs(delta) >= self.min_reward_shift
            comparisons[action] = {
                "status": "shift_detected" if is_shifted else "within_threshold",
                "previous_mean_reward": old_mean,
                "recent_mean_reward": new_mean,
                "reward_shift": delta,
                "previous_samples": len(old),
                "recent_samples": len(new),
                "previous_evidence_ids": [r["id"] for r in old],
                "recent_evidence_ids": [r["id"] for r in new],
            }
            if is_shifted:
                shifted.append(action)

        if not comparisons or all(v["status"] == "insufficient_samples" for v in comparisons.values()):
            return self._result(
                "abstain", "insufficient_action_samples_in_both_windows", context,
                comparisons=comparisons,
                previous_decisions=sorted(previous_ids),
                recent_decisions=sorted(recent_ids),
            )
        return self._result(
            "detected" if shifted else "stable",
            "reward_shift_exceeds_threshold" if shifted else "no_shift_exceeds_threshold",
            context,
            shifted_actions=shifted,
            comparisons=comparisons,
            previous_decisions=sorted(previous_ids),
            recent_decisions=sorted(recent_ids),
            min_reward_shift=self.min_reward_shift,
            interpretation="Observed contextual reward shift; cause is not inferred.",
        )

    @staticmethod
    def _result(status: str, reason: str, context: str, **details: object) -> dict:
        return {"status": status, "reason": reason, "context": context.strip(), **details}
