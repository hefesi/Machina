"""Persistent lifecycle for internally generated Machina goals.

This store tracks goal status and explicit evidence separately from the autonomy
selection ledger. It does not infer success from a completed cognitive cycle.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from .autonomy import GoalCandidate


class PersistentGoalStore:
    """SQLite-backed goal continuity with explicit, auditable transitions."""

    STATUSES = {"active", "completed", "paused", "needs_revision", "abandoned"}
    OUTCOMES = {"success", "failure", "skip"}

    def __init__(self, path: str | Path, *, failures_before_revision: int = 3) -> None:
        if failures_before_revision < 1:
            raise ValueError("failures_before_revision must be positive")
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.failures_before_revision = failures_before_revision
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS persistent_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                drive TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN
                    ('active', 'completed', 'paused', 'needs_revision', 'abandoned')),
                failure_count INTEGER NOT NULL DEFAULT 0,
                evidence TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_persistent_goals_status ON persistent_goals(status, id)"
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def register(self, goal: GoalCandidate) -> dict[str, Any]:
        """Reuse an active instance of the same goal type, otherwise create one."""
        row = self._db.execute(
            "SELECT * FROM persistent_goals WHERE goal_id = ? AND status = 'active' "
            "ORDER BY id DESC LIMIT 1",
            (goal.goal_id,),
        ).fetchone()
        if row is not None:
            self._db.execute(
                "UPDATE persistent_goals SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (row["id"],),
            )
            self._db.commit()
            return self._as_dict(self._db.execute(
                "SELECT * FROM persistent_goals WHERE id = ?", (row["id"],)
            ).fetchone())
        cursor = self._db.execute(
            "INSERT INTO persistent_goals (goal_id, drive, description, status) "
            "VALUES (?, ?, ?, 'active')",
            (goal.goal_id, goal.drive, goal.description),
        )
        self._db.commit()
        return self._as_dict(self._db.execute(
            "SELECT * FROM persistent_goals WHERE id = ?", (cursor.lastrowid,)
        ).fetchone())

    def record_outcome(self, goal_id: str, outcome: str, evidence: str = "") -> dict[str, Any]:
        """Apply explicit feedback; repeated failures flag revision rather than success."""
        if outcome not in self.OUTCOMES:
            raise ValueError("outcome must be success, failure, or skip")
        row = self._db.execute(
            "SELECT * FROM persistent_goals WHERE goal_id = ? AND status IN "
            "('active', 'paused', 'needs_revision') ORDER BY id DESC LIMIT 1",
            (goal_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"no open persistent goal found for {goal_id!r}")
        failures = row["failure_count"] + (1 if outcome == "failure" else 0)
        if outcome == "success":
            status = "completed"
        elif outcome == "skip":
            status = "paused"
        elif failures >= self.failures_before_revision:
            status = "needs_revision"
        else:
            status = "active"
        prior_evidence = row["evidence"]
        new_evidence = evidence.strip()
        if prior_evidence and new_evidence:
            new_evidence = prior_evidence + "\\n" + new_evidence
        elif not new_evidence:
            new_evidence = prior_evidence
        completed_at = "CURRENT_TIMESTAMP" if status == "completed" else "NULL"
        self._db.execute(
            "UPDATE persistent_goals SET status = ?, failure_count = ?, evidence = ?, "
            "updated_at = CURRENT_TIMESTAMP, completed_at = " + completed_at + " WHERE id = ?",
            (status, failures, new_evidence, row["id"]),
        )
        self._db.commit()
        return self._as_dict(self._db.execute(
            "SELECT * FROM persistent_goals WHERE id = ?", (row["id"],)
        ).fetchone())

    def resume(self, goal_id: str) -> dict[str, Any]:
        row = self._db.execute(
            "SELECT * FROM persistent_goals WHERE goal_id = ? AND status IN "
            "('paused', 'needs_revision') ORDER BY id DESC LIMIT 1",
            (goal_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"no paused or revision-needed goal found for {goal_id!r}")
        self._db.execute(
            "UPDATE persistent_goals SET status = 'active', updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?", (row["id"],)
        )
        self._db.commit()
        return self._as_dict(self._db.execute(
            "SELECT * FROM persistent_goals WHERE id = ?", (row["id"],)
        ).fetchone())

    def list_goals(self, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 1:
            return []
        if status is not None and status not in self.STATUSES:
            raise ValueError(f"status must be one of: {', '.join(sorted(self.STATUSES))}")
        if status is None:
            rows = self._db.execute(
                "SELECT * FROM persistent_goals ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM persistent_goals WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        return [self._as_dict(row) for row in rows]

    def summary(self) -> dict[str, int]:
        rows = self._db.execute(
            "SELECT status, COUNT(*) AS count FROM persistent_goals GROUP BY status"
        ).fetchall()
        counts = {status: 0 for status in self.STATUSES}
        counts.update({row["status"]: row["count"] for row in rows})
        counts["total"] = sum(counts.values())
        return counts

    @staticmethod
    def _as_dict(row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)
