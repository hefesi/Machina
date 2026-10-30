"""Adaptive review of successive multi-goal plans.

This module compares plans and records why the proposed trajectory changed.
It does not change goal lifecycle or execute selected goals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .goal_constraints import GoalSchedule
from .goal_store import PersistentGoalStore


@dataclass(frozen=True, slots=True)
class PlanRevision:
    previous_goal_ids: tuple[str, ...]
    selected_goal_ids: tuple[str, ...]
    deferred_goal_ids: tuple[str, ...]
    retained_goal_ids: tuple[str, ...]
    newly_selected_goal_ids: tuple[str, ...]
    newly_deferred_goal_ids: tuple[str, ...]
    restored_goal_ids: tuple[str, ...]
    trigger: str
    rationale: str
    history_record_id: int

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        for key in (
            "previous_goal_ids", "selected_goal_ids", "deferred_goal_ids",
            "retained_goal_ids", "newly_selected_goal_ids",
            "newly_deferred_goal_ids", "restored_goal_ids",
        ):
            result[key] = list(result[key])
        return result


class AdaptivePlanReviewer:
    """Compare a new schedule with the prior plan and persist the explanation."""

    def __init__(self, store: PersistentGoalStore) -> None:
        self.store = store

    def review(
        self,
        previous_goal_ids: tuple[str, ...] | list[str],
        schedule: GoalSchedule,
        *,
        trigger: str,
        context: dict[str, Any] | None = None,
    ) -> PlanRevision:
        previous = tuple(previous_goal_ids)
        if len(set(previous)) != len(previous) or any(
            not isinstance(item, str) or not item.strip() for item in previous
        ):
            raise ValueError("previous_goal_ids must contain unique non-empty strings")
        if not isinstance(schedule, GoalSchedule):
            raise TypeError("schedule must be a GoalSchedule")
        if not isinstance(trigger, str) or not trigger.strip():
            raise ValueError("trigger must be non-empty")
        if context is not None and not isinstance(context, dict):
            raise ValueError("context must be a dictionary")

        selected = tuple(schedule.selected_goal_ids)
        deferred = tuple(schedule.deferred_goal_ids)
        prior, current = set(previous), set(selected)
        retained = tuple(sorted(prior & current))
        newly_selected = tuple(sorted(current - prior))
        newly_deferred = tuple(sorted(prior - current))
        prior_deferred = {
            item
            for record in self.store.recent_plan_revisions(limit=1000)
            for item in record["deferred_goal_ids"]
        }
        restored = tuple(sorted(current & prior_deferred))
        changes = []
        if newly_selected:
            changes.append("novos objetivos selecionados: " + ", ".join(newly_selected))
        if newly_deferred:
            changes.append("objetivos anteriores adiados: " + ", ".join(newly_deferred))
        if restored:
            changes.append("objetivos anteriormente adiados retomados: " + ", ".join(restored))
        if not changes:
            changes.append("a composição do plano foi mantida")
        rationale = schedule.rationale + " Revisão: " + "; ".join(changes) + "."
        record_id = self.store.record_plan_revision(
            previous_goal_ids=list(previous),
            selected_goal_ids=list(selected),
            deferred_goal_ids=list(deferred),
            trigger=trigger,
            rationale=rationale,
            context=context,
        )
        return PlanRevision(
            previous_goal_ids=previous,
            selected_goal_ids=selected,
            deferred_goal_ids=deferred,
            retained_goal_ids=retained,
            newly_selected_goal_ids=newly_selected,
            newly_deferred_goal_ids=newly_deferred,
            restored_goal_ids=restored,
            trigger=trigger.strip(),
            rationale=rationale,
            history_record_id=record_id,
        )
