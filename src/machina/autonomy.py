"""Bounded, inspectable autonomy: generate internal goals and select one safely.

This module implements operational autonomy, not a claim of metaphysical
free will. Goal generation and scoring are explicit so experiments can inspect
why one internal goal was preferred over alternatives.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable


@dataclass(frozen=True, slots=True)
class AutonomyContext:
    """Internal signals available to the goal generator."""

    memory_count: int = 0
    important_memory_count: int = 0
    unresolved_questions: int = 0
    failed_cycles: int = 0
    cycles_since_reflection: int = 0
    cycles_since_memory_review: int = 0

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")


@dataclass(frozen=True, slots=True)
class GoalCandidate:
    """A proposed goal with explicit utility and safety characteristics."""

    goal_id: str
    description: str
    drive: str
    urgency: float
    expected_benefit: float
    confidence: float
    estimated_cost: float
    risk: float
    requires_external_action: bool = False

    def __post_init__(self) -> None:
        if not self.goal_id.strip() or not self.description.strip() or not self.drive.strip():
            raise ValueError("goal_id, description and drive must be non-empty")
        for name in ("urgency", "expected_benefit", "confidence", "estimated_cost", "risk"):
            value = getattr(self, name)
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be finite and between 0 and 1")


@dataclass(frozen=True, slots=True)
class AutonomyDecision:
    selected_goal: GoalCandidate | None
    alternatives: tuple[dict[str, Any], ...]
    rejected: tuple[dict[str, str], ...]
    policy: str = "bounded_utility_v1"

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "selected_goal": asdict(self.selected_goal) if self.selected_goal else None,
            "alternatives": [dict(item) for item in self.alternatives],
            "rejected": [dict(item) for item in self.rejected],
            "interpretation": (
                "Operational goal selection with an inspectable policy; "
                "this is not evidence of conscious free will."
            ),
        }


class AutonomyController:
    """Generate self-directed internal goals and select a safe next goal.

    The controller only selects internal cognitive goals. Candidates requiring
    external actions are rejected by default; this prototype has no implicit
    permission to affect files, networks, accounts, or other external systems.
    """

    def __init__(self, *, max_risk: float = 0.45) -> None:
        if not math.isfinite(max_risk) or not 0.0 <= max_risk <= 1.0:
            raise ValueError("max_risk must be finite and between 0 and 1")
        self.max_risk = max_risk

    def generate_goals(self, context: AutonomyContext) -> list[GoalCandidate]:
        """Propose internal goals from persistent-state and unmet-need signals."""
        goals: list[GoalCandidate] = []

        if context.unresolved_questions:
            goals.append(GoalCandidate(
                "investigate_open_questions",
                "Investigate unresolved questions and identify missing evidence",
                "curiosity",
                min(0.95, 0.45 + 0.1 * context.unresolved_questions),
                0.78, 0.72, 0.42, 0.12,
            ))

        if context.failed_cycles:
            goals.append(GoalCandidate(
                "analyze_recent_failure",
                "Analyze a failed cognitive cycle and propose a safer next experiment",
                "error_recovery",
                min(1.0, 0.55 + 0.1 * context.failed_cycles),
                0.88, 0.85, 0.38, 0.08,
            ))

        if context.important_memory_count and context.cycles_since_memory_review >= 2:
            goals.append(GoalCandidate(
                "review_important_memory",
                "Review high-priority memory fragments for relevance and continuity",
                "memory_maintenance",
                0.68, 0.72, 0.9, 0.22, 0.04,
            ))

        if context.cycles_since_reflection >= 3:
            goals.append(GoalCandidate(
                "reflect_on_progress",
                "Review recent progress and choose the next useful experiment",
                "self_reflection",
                0.85, 0.76, 0.72, 0.3, 0.06,
            ))

        if context.memory_count == 0:
            goals.append(GoalCandidate(
                "establish_memory_baseline",
                "Inspect the current state and identify what should be remembered",
                "continuity",
                0.64, 0.6, 0.9, 0.18, 0.02,
            ))

        goals.append(GoalCandidate(
            "inspect_internal_state",
            "Inspect internal state and decide whether further work is needed",
            "self_monitoring",
            0.15, 0.2, 0.9, 0.08, 0.01,
        ))
        return goals

    @staticmethod
    def _score(goal: GoalCandidate) -> dict[str, float]:
        components = {
            "urgency": 0.30 * goal.urgency,
            "expected_benefit": 0.30 * goal.expected_benefit,
            "confidence": 0.20 * goal.confidence,
            "cost_penalty": -0.15 * goal.estimated_cost,
            "risk_penalty": -0.50 * goal.risk,
        }
        components["total"] = sum(components.values())
        return components

    def choose(
        self,
        candidates: Iterable[GoalCandidate],
        *,
        approved_external_goal_ids: Iterable[str] = (),
    ) -> AutonomyDecision:
        """Choose the highest-scoring eligible goal and retain the rationale."""
        goals = list(candidates)
        if len({goal.goal_id for goal in goals}) != len(goals):
            raise ValueError("goal_id values must be unique")
        approved = set(approved_external_goal_ids)
        eligible: list[tuple[GoalCandidate, dict[str, float]]] = []
        rejected: list[dict[str, str]] = []

        for goal in goals:
            if goal.risk > self.max_risk:
                rejected.append({"goal_id": goal.goal_id, "reason": "risk_above_limit"})
                continue
            if goal.requires_external_action and goal.goal_id not in approved:
                rejected.append({"goal_id": goal.goal_id, "reason": "external_action_not_authorized"})
                continue
            eligible.append((goal, self._score(goal)))

        eligible.sort(key=lambda pair: (-pair[1]["total"], pair[0].goal_id))
        alternatives = tuple(
            {"goal": asdict(goal), "score": score}
            for goal, score in eligible
        )
        return AutonomyDecision(
            selected_goal=eligible[0][0] if eligible else None,
            alternatives=alternatives,
            rejected=tuple(rejected),
        )

    def step(self, context: AutonomyContext) -> AutonomyDecision:
        """Generate and choose one internal goal from current internal signals."""
        return self.choose(self.generate_goals(context))
