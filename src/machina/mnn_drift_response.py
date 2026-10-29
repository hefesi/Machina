"""Conservative response recommendations for detected reward drift.

This policy translates drift evidence into review/exploration recommendations.
It deliberately does not mutate the learner or delete/rewrite historical memory.
"""
from __future__ import annotations

import math
from collections.abc import Mapping


class MNNDriftResponsePolicy:
    """Recommend next steps from an MNNRewardDriftDetector result."""

    def evaluate(self, drift_result: Mapping) -> dict:
        if not isinstance(drift_result, Mapping):
            raise ValueError("drift_result must be a mapping")
        status = drift_result.get("status")
        if status not in {"detected", "stable", "abstain"}:
            raise ValueError("drift_result status must be detected, stable, or abstain")

        context = drift_result.get("context", "")
        if not isinstance(context, str):
            raise ValueError("drift context must be a string")
        reason = drift_result.get("reason")
        if not isinstance(reason, str) or not reason:
            raise ValueError("drift reason must be a non-empty string")

        if status == "abstain":
            return {
                "status": "insufficient_evidence",
                "context": context,
                "reason": reason,
                "response": "collect_more_evidence",
                "suggested_actions": [
                    "Continue recording outcomes with decision, action, reward, and context.",
                    "Re-evaluate only after both comparison windows have enough observations.",
                ],
                "changes_learner": False,
                "preserves_history": True,
            }

        if status == "stable":
            return {
                "status": "stable",
                "context": context,
                "reason": reason,
                "response": "continue_monitoring",
                "shifted_actions": [],
                "degraded_actions": [],
                "improved_actions": [],
                "changes_learner": False,
                "preserves_history": True,
            }

        comparisons = drift_result.get("comparisons")
        if not isinstance(comparisons, Mapping) or not comparisons:
            raise ValueError("detected drift must include non-empty comparisons")

        degraded = []
        improved = []
        evidence_ids = []
        for action, comparison in comparisons.items():
            if not isinstance(action, str) or not isinstance(comparison, Mapping):
                raise ValueError("each comparison must map an action name to evidence")
            if comparison.get("status") != "shift_detected":
                continue
            shift = comparison.get("reward_shift")
            if isinstance(shift, bool) or not isinstance(shift, (int, float)) or not math.isfinite(shift):
                raise ValueError("shift_detected comparisons need a finite reward_shift")
            if shift < 0:
                degraded.append(action)
            elif shift > 0:
                improved.append(action)
            for key in ("previous_evidence_ids", "recent_evidence_ids"):
                ids = comparison.get(key, [])
                if not isinstance(ids, list) or any(not isinstance(item, str) for item in ids):
                    raise ValueError("evidence ID fields must be lists of strings")
                evidence_ids.extend(ids)

        if not degraded and not improved:
            raise ValueError("detected drift must contain at least one non-zero shifted action")

        return {
            "status": "drift_detected",
            "context": context,
            "reason": reason,
            "response": "increase_exploration_and_reassess",
            "degraded_actions": sorted(degraded),
            "improved_actions": sorted(improved),
            "shifted_actions": sorted(set(degraded + improved)),
            "evidence_ids": sorted(set(evidence_ids)),
            "suggested_actions": [
                "Temporarily gather more evidence before relying on the previous action ranking.",
                "Compare alternatives in the same context and record their outcomes.",
                "Re-evaluate the drift signal after a fresh decision window.",
            ],
            "changes_learner": False,
            "preserves_history": True,
            "interpretation": (
                "This is a decision-support recommendation. It does not infer the "
                "cause of drift, reset learned values, or prove that the environment changed."
            ),
        }
