"""Evidence-based review of persistent goals.

Review is advisory and side-effect free. Applying a review requires an
explicit caller decision and evaluator-supplied evidence.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

from .goal_store import PersistentGoalStore


@dataclass(frozen=True, slots=True)
class GoalReview:
    goal_id: str
    record_id: int
    prior_status: str
    prior_progress: float
    observed_progress: float
    progress_delta: float
    prior_priority: float
    proposed_priority: float | None
    recommendation: str
    evidence: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class GoalReviewer:
    """Compare an evaluator's latest measurement with durable goal state."""

    def __init__(self, store: PersistentGoalStore) -> None:
        self.store = store

    def review(
        self,
        goal_id: str,
        *,
        observed_progress: float,
        evidence: str,
        proposed_priority: float | None = None,
    ) -> GoalReview:
        if isinstance(observed_progress, bool) or not isinstance(observed_progress, (int, float)) or not math.isfinite(observed_progress) or not 0.0 <= observed_progress <= 1.0:
            raise ValueError("observed_progress must be finite and between 0 and 1")
        if proposed_priority is not None and (
            isinstance(proposed_priority, bool) or not isinstance(proposed_priority, (int, float))
            or not math.isfinite(proposed_priority) or not 0.0 <= proposed_priority <= 1.0
        ):
            raise ValueError("proposed_priority must be finite and between 0 and 1")
        note = evidence.strip()
        if not note:
            raise ValueError("review requires explicit evidence")
        matches = [
            item for item in self.store.list_goals(limit=1000)
            if item["goal_id"] == goal_id and item["status"] in {"active", "needs_revision"}
        ]
        if not matches:
            raise ValueError(f"no reviewable goal found for {goal_id!r}")
        record = matches[0]
        previous = float(record["progress"])
        delta = float(observed_progress) - previous
        if record["status"] == "needs_revision" or delta < 0:
            recommendation = "revise"
        elif delta > 0:
            recommendation = "continue"
        else:
            recommendation = "reassess"
        return GoalReview(
            goal_id=goal_id,
            record_id=int(record["id"]),
            prior_status=record["status"],
            prior_progress=previous,
            observed_progress=float(observed_progress),
            progress_delta=delta,
            prior_priority=float(record["priority"]),
            proposed_priority=float(proposed_priority) if proposed_priority is not None else None,
            recommendation=recommendation,
            evidence=note,
        )

    def apply(
        self,
        review: GoalReview,
        *,
        outcome: str | None = None,
    ) -> dict[str, Any]:
        """Persist a reviewed measurement; outcome transitions are explicit."""
        if not isinstance(review, GoalReview):
            raise TypeError("review must be a GoalReview")
        if outcome is not None:
            return self.store.record_outcome(
                review.goal_id,
                outcome,
                evidence=review.evidence,
                record_id=review.record_id,
                expected_progress=review.prior_progress,
            )
        return self.store.update_progress(
            review.goal_id,
            review.observed_progress,
            evidence=review.evidence,
            priority=review.proposed_priority,
            record_id=review.record_id,
            expected_progress=review.prior_progress,
        )
