"""Auditable hierarchical planning with persistent steps and dependencies.

Plans are deliberately templates and explicit state transitions, not proof of
semantic reasoning. A step is completed only after explicit evaluation.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


_PLAN_TEMPLATES: dict[str, list[tuple[str, str, list[int]]]] = {
    "investigate_open_questions": [
        ("clarify_question", "Restate the question and define what is unknown", []),
        ("identify_evidence", "List the evidence needed to answer the question", [0]),
        ("compare_evidence", "Compare available evidence against the requirements", [1]),
        ("record_conclusion", "Record a qualified conclusion and remaining uncertainty", [2]),
    ],
    "analyze_recent_failure": [
        ("inspect_failure", "Inspect the failed cycle and preserve its evidence", []),
        ("form_hypotheses", "List plausible causes without treating them as facts", [0]),
        ("design_test", "Define a small test that distinguishes the hypotheses", [1]),
        ("evaluate_test", "Evaluate the test result and revise the next attempt", [2]),
    ],
    "review_important_memory": [
        ("retrieve_fragments", "Retrieve the relevant high-priority memory fragments", []),
        ("check_consistency", "Check provenance, relevance, and apparent contradictions", [0]),
        ("propose_updates", "Propose additions or revisions without deleting source history", [1]),
        ("verify_updates", "Verify the proposed memory changes and record evidence", [2]),
    ],
    "reflect_on_progress": [
        ("summarize_progress", "Summarize recorded goals, outcomes, and unresolved work", []),
        ("compare_results", "Compare explicit outcomes with the intended criteria", [0]),
        ("select_experiment", "Choose a measurable next experiment from the evidence", [1]),
        ("record_next_goal", "Record the next goal and its success criteria", [2]),
    ],
    "establish_memory_baseline": [
        ("inspect_memory", "Inspect the current memory inventory and priorities", []),
        ("identify_gaps", "Identify missing context and likely continuity gaps", [0]),
        ("propose_baseline", "Propose a minimal baseline of useful memory fragments", [1]),
        ("verify_baseline", "Verify that the baseline is saved and retrievable", [2]),
    ],
    "inspect_internal_state": [
        ("inspect_state", "Inspect current system state and recent audit records", []),
        ("identify_issue", "Identify a concrete issue or record that no issue was found", [0]),
        ("choose_followup", "Choose a justified follow-up or conclude the review", [1]),
    ],
}


class HierarchicalPlanner:
    """Expand a top-level goal into an ordered, inspectable plan."""

    def decompose(self, goal_id: str, description: str) -> list[dict[str, Any]]:
        if not goal_id.strip() or not description.strip():
            raise ValueError("goal_id and description must be non-empty")
        template = _PLAN_TEMPLATES.get(goal_id)
        if template is None:
            template = [
                ("define_success", f"Define observable success criteria for: {description}", []),
                ("inspect_context", "Inspect relevant memory and available evidence", [0]),
                ("perform_next_action", "Perform one bounded internal step toward the goal", [1]),
                ("evaluate_result", "Evaluate the result and record evidence before continuing", [2]),
            ]
        steps: list[dict[str, Any]] = []
        for index, (step_key, step_description, dependency_indices) in enumerate(template, start=1):
            steps.append({
                "step_id": f"{goal_id}:{index:02d}:{step_key}",
                "order": index,
                "key": step_key,
                "description": step_description,
                "dependencies": [
                    f"{goal_id}:{dep + 1:02d}:{template[dep][0]}"
                    for dep in dependency_indices
                ],
            })
        return steps


class PersistentPlanStore:
    """SQLite storage for plans, ordered steps, dependencies, and explicit evidence."""

    PLAN_STATUSES = {"active", "completed", "paused", "needs_revision", "abandoned"}
    STEP_STATUSES = {"pending", "ready", "completed", "paused", "needs_revision", "blocked"}

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_record_id INTEGER NOT NULL,
                goal_id TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN
                    ('active','completed','paused','needs_revision','abandoned')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS plan_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL REFERENCES plans(id),
                step_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                step_key TEXT NOT NULL,
                description TEXT NOT NULL,
                dependencies TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL CHECK(status IN
                    ('pending','ready','completed','paused','needs_revision','blocked')),
                evidence TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(plan_id, step_id)
            )
        """)
        self._db.execute("CREATE INDEX IF NOT EXISTS idx_plan_steps_order ON plan_steps(plan_id, step_order)")
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def create_plan(
        self,
        goal_record: dict[str, Any],
        planner: HierarchicalPlanner | None = None,
    ) -> dict[str, Any]:
        required = ("id", "goal_id", "description", "status")
        if any(key not in goal_record for key in required):
            raise ValueError("goal record must include id, goal_id, description, and status")
        if goal_record["status"] not in {"active", "needs_revision", "paused"}:
            raise ValueError("only open goals can receive a plan")
        existing = self._db.execute(
            "SELECT * FROM plans WHERE goal_record_id = ? AND status IN "
            "('active','paused','needs_revision') ORDER BY id DESC LIMIT 1",
            (goal_record["id"],),
        ).fetchone()
        if existing is not None:
            return self.get_plan(existing["id"])
        steps = (planner or HierarchicalPlanner()).decompose(
            str(goal_record["goal_id"]), str(goal_record["description"])
        )
        cursor = self._db.execute(
            "INSERT INTO plans (goal_record_id, goal_id, description, status) "
            "VALUES (?, ?, ?, 'active')",
            (goal_record["id"], goal_record["goal_id"], goal_record["description"]),
        )
        plan_id = int(cursor.lastrowid)
        for step in steps:
            self._db.execute(
                "INSERT INTO plan_steps (plan_id, step_id, step_order, step_key, description, "
                "dependencies, status) VALUES (?, ?, ?, ?, ?, ?, 'pending')",
                (plan_id, step["step_id"], step["order"], step["key"], step["description"],
                 json.dumps(step["dependencies"], ensure_ascii=False)),
            )
        self._db.commit()
        return self.get_plan(plan_id)

    def get_plan(self, plan_id: int) -> dict[str, Any]:
        row = self._db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
        if row is None:
            raise ValueError(f"plan {plan_id} was not found")
        plan = dict(row)
        plan["steps"] = [self._step_dict(item) for item in self._db.execute(
            "SELECT * FROM plan_steps WHERE plan_id = ? ORDER BY step_order", (plan_id,)
        ).fetchall()]
        return plan

    def list_plans(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 1:
            return []
        if status is not None and status not in self.PLAN_STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(self.PLAN_STATUSES))}")
        if status is None:
            rows = self._db.execute("SELECT id FROM plans ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        else:
            rows = self._db.execute(
                "SELECT id FROM plans WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit)
            ).fetchall()
        return [self.get_plan(row["id"]) for row in rows]

    def ready_steps(self, plan_id: int) -> list[dict[str, Any]]:
        plan = self.get_plan(plan_id)
        if plan["status"] != "active":
            return []
        completed = {s["step_id"] for s in plan["steps"] if s["status"] == "completed"}
        ready = []
        for step in plan["steps"]:
            if step["status"] != "pending":
                continue
            dependencies = step["dependencies"]
            if all(dependency in completed for dependency in dependencies):
                ready.append(step)
        return ready

    def record_step_outcome(
        self, plan_id: int, step_id: str, outcome: str, evidence: str = ""
    ) -> dict[str, Any]:
        if outcome not in {"success", "failure", "skip"}:
            raise ValueError("outcome must be success, failure, or skip")
        plan = self.get_plan(plan_id)
        if plan["status"] != "active":
            raise ValueError(f"plan {plan_id} is not active")
        ready = {step["step_id"] for step in self.ready_steps(plan_id)}
        if step_id not in ready:
            raise ValueError("step is not ready; dependencies may be incomplete or step already evaluated")
        row = self._db.execute(
            "SELECT * FROM plan_steps WHERE plan_id = ? AND step_id = ?", (plan_id, step_id)
        ).fetchone()
        status = {"success": "completed", "failure": "needs_revision", "skip": "paused"}[outcome]
        prior = row["evidence"]
        current = evidence.strip()
        combined = prior + "\n" + current if prior and current else (current or prior)
        self._db.execute(
            "UPDATE plan_steps SET status = ?, evidence = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (status, combined, row["id"]),
        )
        if outcome == "failure":
            plan_status = "needs_revision"
        elif outcome == "skip":
            plan_status = "paused"
        else:
            remaining = self._db.execute(
                "SELECT COUNT(*) AS n FROM plan_steps WHERE plan_id = ? AND status != 'completed'",
                (plan_id,),
            ).fetchone()["n"]
            plan_status = "completed" if remaining == 0 else "active"
        self._db.execute(
            "UPDATE plans SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (plan_status, plan_id),
        )
        self._db.commit()
        return self.get_plan(plan_id)

    def resume_plan(self, plan_id: int) -> dict[str, Any]:
        plan = self.get_plan(plan_id)
        if plan["status"] not in {"paused", "needs_revision"}:
            raise ValueError("only paused or revision-needed plans can be resumed")
        self._db.execute(
            "UPDATE plans SET status = 'active', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (plan_id,),
        )
        self._db.execute(
            "UPDATE plan_steps SET status = 'pending', updated_at = CURRENT_TIMESTAMP "
            "WHERE plan_id = ? AND status IN ('paused','needs_revision')", (plan_id,)
        )
        self._db.commit()
        return self.get_plan(plan_id)

    def summary(self) -> dict[str, int]:
        rows = self._db.execute("SELECT status, COUNT(*) AS n FROM plans GROUP BY status").fetchall()
        counts = {status: 0 for status in self.PLAN_STATUSES}
        counts.update({row["status"]: row["n"] for row in rows})
        counts["total"] = sum(counts.values())
        return counts

    @staticmethod
    def _step_dict(row: sqlite3.Row) -> dict[str, Any]:
        step = dict(row)
        step["dependencies"] = json.loads(step["dependencies"])
        return step
