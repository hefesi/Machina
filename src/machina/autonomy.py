"""Bounded, inspectable autonomy: generate internal goals and select one safely.

This module implements operational autonomy, not a claim of metaphysical
free will. Goal generation and scoring are explicit so experiments can inspect
why one internal goal was preferred over alternatives.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import sqlite3
from pathlib import Path
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
    policy: str = "bounded_utility_feedback_v2"

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy": self.policy,
            "selected_goal": asdict(self.selected_goal) if self.selected_goal else None,
            "alternatives": [dict(item) for item in self.alternatives],
            "rejected": [dict(item) for item in self.rejected],
            "interpretation": (
                "Operational goal selection with an inspectable policy and optional "
                "feedback adjustments; this is not evidence of conscious free will."
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
        drive_adjustments: dict[str, float] | None = None,
        recent_goal_ids: Iterable[str] = (),
        commitment_alignment: dict[str, float] | None = None,
        commitment_weight: float = 0.10,
    ) -> AutonomyDecision:
        """Choose an eligible goal with bounded, explicit commitment alignment.

        Alignment values must be supplied by an evidence-aware evaluator for
        the current persistent commitments. They are never inferred from goal
        wording here. This keeps the autonomy policy auditable and avoids
        treating a text match as proof that a goal honors a commitment.
        """
        if isinstance(commitment_weight, bool) or not isinstance(commitment_weight, (int, float)) or not math.isfinite(commitment_weight) or not 0.0 <= commitment_weight <= 0.15:
            raise ValueError("commitment_weight must be finite and within [0, 0.15]")
        alignments = dict(commitment_alignment or {})
        for goal_id, alignment in alignments.items():
            if not isinstance(goal_id, str) or not goal_id.strip():
                raise ValueError("commitment alignment keys must be non-empty goal IDs")
            if isinstance(alignment, bool) or not isinstance(alignment, (int, float)) or not math.isfinite(alignment) or not 0.0 <= alignment <= 1.0:
                raise ValueError("commitment alignment values must be finite and within [0, 1]")
        goals = list(candidates)
        if len({goal.goal_id for goal in goals}) != len(goals):
            raise ValueError("goal_id values must be unique")
        approved = set(approved_external_goal_ids)
        recent = set(recent_goal_ids)
        adjustments = drive_adjustments or {}
        eligible: list[tuple[GoalCandidate, dict[str, float]]] = []
        rejected: list[dict[str, str]] = []

        for goal in goals:
            if goal.risk > self.max_risk:
                rejected.append({"goal_id": goal.goal_id, "reason": "risk_above_limit"})
                continue
            if goal.requires_external_action and goal.goal_id not in approved:
                rejected.append({"goal_id": goal.goal_id, "reason": "external_action_not_authorized"})
                continue
            score = self._score(goal)
            feedback = max(-0.15, min(0.15, float(adjustments.get(goal.drive, 0.0))))
            repetition = -0.08 if goal.goal_id in recent else 0.0
            score["base_total"] = score["total"]
            score["feedback_adjustment"] = feedback
            score["repetition_penalty"] = repetition
            alignment = float(alignments.get(goal.goal_id, 0.0))
            score["commitment_alignment"] = alignment
            score["commitment_adjustment"] = float(commitment_weight) * alignment
            score["total"] = score["base_total"] + feedback + repetition + score["commitment_adjustment"]
            eligible.append((goal, score))

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

    def generate_motivational_goals(self, motivation: Any, *, threshold: float = 0.25) -> list[GoalCandidate]:
        """Turn sustained internal pressure into inspectable internal goals.

        The motivation object is intentionally consumed through a small
        structural interface to avoid coupling the autonomy layer to a
        particular neural implementation.
        """
        if not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be finite and between 0 and 1")
        if not hasattr(motivation, "temporal_urgencies"):
            raise ValueError("motivation must expose temporal_urgencies()")
        pressures = motivation.temporal_urgencies()
        if not isinstance(pressures, dict):
            raise ValueError("temporal_urgencies() must return a mapping")
        goals: list[GoalCandidate] = []
        for drive, pressure in sorted(pressures.items()):
            if not isinstance(drive, str) or not drive.strip():
                raise ValueError("motivational drive names must be non-empty strings")
            if isinstance(pressure, bool) or not isinstance(pressure, (int, float)) or not math.isfinite(pressure) or not 0.0 <= pressure <= 1.0:
                raise ValueError(f"invalid temporal pressure for drive: {drive}")
            if pressure < threshold:
                continue
            goals.append(GoalCandidate(
                goal_id=f"sustain_drive:{drive}",
                description=f"Address the sustained internal pressure associated with {drive}",
                drive=drive,
                urgency=float(pressure),
                expected_benefit=0.55,
                confidence=0.65,
                estimated_cost=0.25,
                risk=0.02,
            ))
        return goals

    def step(
        self,
        context: AutonomyContext,
        *,
        drive_adjustments: dict[str, float] | None = None,
        recent_goal_ids: Iterable[str] = (),
        motivation: Any | None = None,
        commitment_alignment: dict[str, float] | None = None,
        commitment_weight: float = 0.10,
    ) -> AutonomyDecision:
        """Generate and choose a goal from context and sustained internal pressure."""
        candidates = self.generate_goals(context)
        adjustments = dict(drive_adjustments or {})
        if motivation is not None:
            candidates.extend(self.generate_motivational_goals(motivation))
            if hasattr(motivation, "temporal_autonomy_adjustments"):
                adjustments.update(motivation.temporal_autonomy_adjustments())
        return self.choose(
            candidates,
            drive_adjustments=adjustments,
            recent_goal_ids=recent_goal_ids,
            commitment_alignment=commitment_alignment,
            commitment_weight=commitment_weight,
        )


class AutonomyExperienceStore:
    """SQLite ledger for goal choices and explicit human outcome feedback.

    A completed cognitive cycle is not assumed to mean the selected goal
    succeeded. Success/failure is recorded only when feedback is supplied.
    """

    VALID_OUTCOMES = {"success", "failure", "skip"}

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS goal_experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                drive TEXT NOT NULL,
                description TEXT NOT NULL,
                outcome TEXT CHECK (outcome IN ('success', 'failure', 'skip') OR outcome IS NULL),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                feedback_at TEXT
            )
            """
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def record_selection(self, goal: GoalCandidate) -> int:
        cursor = self._db.execute(
            "INSERT INTO goal_experiences (goal_id, drive, description) VALUES (?, ?, ?)",
            (goal.goal_id, goal.drive, goal.description),
        )
        self._db.commit()
        return int(cursor.lastrowid)

    def record_feedback(self, outcome: str) -> dict[str, Any]:
        if outcome not in self.VALID_OUTCOMES:
            raise ValueError("outcome must be success, failure, or skip")
        row = self._db.execute(
            "SELECT id, goal_id, drive, description FROM goal_experiences "
            "WHERE outcome IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if row is None:
            raise ValueError("there is no pending goal to evaluate")
        self._db.execute(
            "UPDATE goal_experiences SET outcome = ?, feedback_at = CURRENT_TIMESTAMP WHERE id = ?",
            (outcome, row["id"]),
        )
        self._db.commit()
        return {**dict(row), "outcome": outcome}

    def drive_adjustments(self) -> dict[str, float]:
        rows = self._db.execute(
            "SELECT drive, SUM(CASE outcome WHEN 'success' THEN 1 "
            "WHEN 'failure' THEN -1 ELSE 0 END) AS net, "
            "SUM(CASE WHEN outcome IN ('success', 'failure') THEN 1 ELSE 0 END) AS n "
            "FROM goal_experiences GROUP BY drive"
        ).fetchall()
        # Two neutral prior observations prevent one report from dominating.
        return {
            row["drive"]: max(-0.15, min(0.15, 0.15 * row["net"] / (row["n"] + 2)))
            for row in rows if row["n"]
        }

    def recent_goal_ids(self, limit: int = 3) -> list[str]:
        if limit < 1:
            return []
        rows = self._db.execute(
            "SELECT goal_id FROM goal_experiences ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [row["goal_id"] for row in rows]

    def summary(self) -> dict[str, Any]:
        row = self._db.execute(
            "SELECT COUNT(*) AS total, "
            "SUM(CASE WHEN outcome = 'success' THEN 1 ELSE 0 END) AS successes, "
            "SUM(CASE WHEN outcome = 'failure' THEN 1 ELSE 0 END) AS failures, "
            "SUM(CASE WHEN outcome IS NULL THEN 1 ELSE 0 END) AS pending "
            "FROM goal_experiences"
        ).fetchone()
        return {
            "goals_recorded": row["total"],
            "successes": row["successes"] or 0,
            "failures": row["failures"] or 0,
            "pending_feedback": row["pending"] or 0,
            "drive_adjustments": self.drive_adjustments(),
        }
