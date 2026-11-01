"""Inspectable internal deliberation over generated and persistent goals.

This is an operational selection cycle. It does not execute goals or imply
phenomenal consciousness, subjective desire, or philosophical free will.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .autonomy import (
    AutonomyContext,
    AutonomyController,
    AutonomyDecision,
    GoalCandidate,
)
from .goal_store import PersistentGoalStore


@dataclass(frozen=True, slots=True)
class DeliberationDecision:
    """One auditable selection and its alternatives."""

    cycle: int
    selected_goal: GoalCandidate | None
    selected_source: str | None
    persistent_record_id: int | None
    autonomy: AutonomyDecision
    rationale: str
    history_record_id: int | None = None
    previous_goal_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "selected_goal": asdict(self.selected_goal) if self.selected_goal else None,
            "selected_source": self.selected_source,
            "persistent_record_id": self.persistent_record_id,
            "autonomy": self.autonomy.to_dict(),
            "rationale": self.rationale,
            "history_record_id": self.history_record_id,
            "previous_goal_id": self.previous_goal_id,
            "interpretation": (
                "A bounded, deterministic operational deliberation record; "
                "selection is not evidence of subjective experience."
            ),
        }


class InternalDeliberator:
    """Compare new proposals with durable open goals and select one next focus.

    Existing open goals are represented in the same bounded scoring policy as
    generated proposals. A selected new goal is persisted only after selection.
    No goal is executed, completed, paused, or abandoned by this class.
    """

    def __init__(
        self,
        controller: AutonomyController,
        goals: PersistentGoalStore,
    ) -> None:
        self.controller = controller
        self.goals = goals
        self._cycle = 0

    @staticmethod
    def _from_persistent(record: dict[str, Any]) -> GoalCandidate:
        # Persistent priority and remaining work become explicit inputs to the
        # common policy; estimates are deliberately conservative and inspectable.
        return GoalCandidate(
            goal_id=record["goal_id"],
            description=record["description"],
            drive=record["drive"],
            urgency=float(record["priority"]),
            expected_benefit=max(0.0, 1.0 - float(record["progress"])),
            confidence=0.75,
            estimated_cost=0.25,
            risk=0.02,
        )

    def deliberate(
        self,
        context: AutonomyContext,
        *,
        motivation: Any | None = None,
        drive_adjustments: dict[str, float] | None = None,
        recent_goal_ids: tuple[str, ...] | list[str] = (),
        open_goal_limit: int = 20,
    ) -> DeliberationDecision:
        """Run one cycle and return the selected focus with score rationale."""
        if isinstance(open_goal_limit, bool) or not isinstance(open_goal_limit, int) or open_goal_limit < 1:
            raise ValueError("open_goal_limit must be a positive integer")

        history = self.goals.recent_deliberations(3)
        previous_goal_id = history[0]["selected_goal_id"] if history else None
        historical_goal_ids = [item["selected_goal_id"] for item in history if isinstance(item.get("selected_goal_id"), str)]
        records = self.goals.ranked_open_goals(open_goal_limit)
        persistent_by_goal = {record["goal_id"]: record for record in records}
        candidates = self.controller.generate_goals(context)
        if motivation is not None:
            candidates.extend(self.controller.generate_motivational_goals(motivation))

        # Prefer the durable representation when a proposal matches an already
        # open goal. This prevents duplicate candidates and preserves its progress.
        candidates_by_id = {goal.goal_id: goal for goal in candidates}
        for record in records:
            candidates_by_id[record["goal_id"]] = self._from_persistent(record)

        adjustments = dict(drive_adjustments or {})
        if motivation is not None and hasattr(motivation, "temporal_autonomy_adjustments"):
            temporal_adjustments = motivation.temporal_autonomy_adjustments()
            for drive, adjustment in temporal_adjustments.items():
                combined = float(adjustments.get(drive, 0.0)) + float(adjustment)
                adjustments[drive] = max(-0.3, min(0.3, combined))

        decision = self.controller.choose(
            candidates_by_id.values(),
            drive_adjustments=adjustments,
            recent_goal_ids=tuple(dict.fromkeys([*recent_goal_ids, *historical_goal_ids])),
        )
        self._cycle += 1
        selected = decision.selected_goal
        source: str | None = None
        record_id: int | None = None
        if selected is not None:
            existing = persistent_by_goal.get(selected.goal_id)
            if existing is not None:
                source = "persistent"
                record_id = int(existing["id"])
            else:
                source = "generated"
                persisted = self.goals.register(selected)
                record_id = int(persisted["id"])

        rationale = (
            "Nenhum objetivo elegível passou pela política de risco."
            if selected is None
            else (
                f"Selecionado '{selected.goal_id}' por obter a maior pontuação "
                "entre os objetivos elegíveis; os componentes estão registrados "
                "nas alternativas da decisão."
            )
        )
        context_snapshot = {
            "unresolved_questions": context.unresolved_questions,
            "failed_cycles": context.failed_cycles,
            "cycles_since_reflection": context.cycles_since_reflection,
            "cycles_since_memory_review": context.cycles_since_memory_review,
            "memory_count": context.memory_count,
            "important_memory_count": context.important_memory_count,
        }
        history_record_id = self.goals.record_deliberation(
            selected_goal_id=selected.goal_id if selected else None,
            selected_source=source,
            rationale=rationale,
            alternatives=list(decision.alternatives),
            context=context_snapshot,
        )
        return DeliberationDecision(
            cycle=self._cycle,
            selected_goal=selected,
            selected_source=source,
            persistent_record_id=record_id,
            autonomy=decision,
            rationale=rationale,
            history_record_id=history_record_id,
            previous_goal_id=previous_goal_id,
        )
