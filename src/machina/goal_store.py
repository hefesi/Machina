"""Persistent lifecycle for internally generated Machina goals.

This store tracks goal status and explicit evidence separately from the autonomy
selection ledger. It does not infer success from a completed cognitive cycle.
"""
from __future__ import annotations

import sqlite3
import json
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
                progress REAL NOT NULL DEFAULT 0.0 CHECK (progress >= 0.0 AND progress <= 1.0),
                priority REAL NOT NULL DEFAULT 0.5 CHECK (priority >= 0.0 AND priority <= 1.0),
                evidence TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT
            )
            """
        )
        columns = {row["name"] for row in self._db.execute("PRAGMA table_info(persistent_goals)")}
        if "progress" not in columns:
            self._db.execute("ALTER TABLE persistent_goals ADD COLUMN progress REAL NOT NULL DEFAULT 0.0")
        if "priority" not in columns:
            self._db.execute("ALTER TABLE persistent_goals ADD COLUMN priority REAL NOT NULL DEFAULT 0.5")
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_persistent_goals_status ON persistent_goals(status, id)"
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS deliberation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                selected_goal_id TEXT,
                selected_source TEXT,
                rationale TEXT NOT NULL,
                alternatives_json TEXT NOT NULL,
                context_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS goal_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_goal_id TEXT NOT NULL,
                target_goal_id TEXT NOT NULL,
                relation TEXT NOT NULL CHECK (relation IN ('conflicts', 'supports', 'requires')),
                strength REAL NOT NULL CHECK (strength >= 0.0 AND strength <= 1.0),
                evidence TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_goal_id, target_goal_id, relation)
            )
            """
        )
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS plan_revision_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                previous_goal_ids_json TEXT NOT NULL,
                selected_goal_ids_json TEXT NOT NULL,
                deferred_goal_ids_json TEXT NOT NULL,
                trigger TEXT NOT NULL,
                rationale TEXT NOT NULL,
                context_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
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

    def update_progress(
        self,
        goal_id: str,
        progress: float,
        *,
        evidence: str,
        priority: float | None = None,
        record_id: int | None = None,
        expected_progress: float | None = None,
    ) -> dict[str, Any]:
        """Record measured progress and optional priority for an open goal.

        Progress is an explicit estimate supplied by an evaluator. It may move
        in either direction when new evidence invalidates earlier assumptions.
        """
        import math

        if isinstance(progress, bool) or not isinstance(progress, (int, float)) or not math.isfinite(progress) or not 0.0 <= progress <= 1.0:
            raise ValueError("progress must be finite and between 0 and 1")
        if priority is not None and (
            isinstance(priority, bool) or not isinstance(priority, (int, float))
            or not math.isfinite(priority) or not 0.0 <= priority <= 1.0
        ):
            raise ValueError("priority must be finite and between 0 and 1")
        note = evidence.strip()
        if not note:
            raise ValueError("progress updates require non-empty evidence")
        query = (
            "SELECT * FROM persistent_goals WHERE goal_id = ? AND status IN "
            "('active', 'needs_revision')"
        )
        params: tuple[Any, ...] = (goal_id,)
        if record_id is not None:
            query += " AND id = ?"
            params += (record_id,)
        query += " ORDER BY id DESC LIMIT 1"
        row = self._db.execute(query, params).fetchone()
        if row is None:
            raise ValueError(f"no matching open persistent goal found for {goal_id!r}")
        if expected_progress is not None and float(row["progress"]) != float(expected_progress):
            raise ValueError("goal changed since review; create a fresh review")
        combined = row["evidence"] + "\\n" + note if row["evidence"] else note
        if priority is None:
            self._db.execute(
                "UPDATE persistent_goals SET progress = ?, evidence = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (float(progress), combined, row["id"]),
            )
        else:
            self._db.execute(
                "UPDATE persistent_goals SET progress = ?, priority = ?, evidence = ?, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (float(progress), float(priority), combined, row["id"]),
            )
        self._db.commit()
        return self._as_dict(self._db.execute(
            "SELECT * FROM persistent_goals WHERE id = ?", (row["id"],)
        ).fetchone())

    def record_outcome(
        self, goal_id: str, outcome: str, evidence: str = "",
        *, record_id: int | None = None, expected_progress: float | None = None,
    ) -> dict[str, Any]:
        """Apply explicit feedback; repeated failures flag revision rather than success."""
        if outcome not in self.OUTCOMES:
            raise ValueError("outcome must be success, failure, or skip")
        query = (
            "SELECT * FROM persistent_goals WHERE goal_id = ? AND status IN "
            "('active', 'needs_revision')"
        )
        params: tuple[Any, ...] = (goal_id,)
        if record_id is not None:
            query += " AND id = ?"
            params += (record_id,)
        query += " ORDER BY id DESC LIMIT 1"
        row = self._db.execute(query, params).fetchone()
        if row is None:
            raise ValueError(f"no matching open persistent goal found for {goal_id!r}")
        if expected_progress is not None and float(row["progress"]) != float(expected_progress):
            raise ValueError("goal changed since review; create a fresh review")
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
            new_evidence = prior_evidence + "\n" + new_evidence
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

    def abandon(self, goal_id: str, evidence: str) -> dict[str, Any]:
        """Explicitly abandon an open goal and retain the reason as evidence."""
        reason = evidence.strip()
        if not reason:
            raise ValueError("abandonment requires a non-empty evidence/reason")
        row = self._db.execute(
            "SELECT * FROM persistent_goals WHERE goal_id = ? AND status IN "
            "('active', 'paused', 'needs_revision') ORDER BY id DESC LIMIT 1",
            (goal_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"no open persistent goal found for {goal_id!r}")
        prior_evidence = row["evidence"]
        new_evidence = prior_evidence + "\n" + "ABANDONED: " + reason if prior_evidence else "ABANDONED: " + reason
        self._db.execute(
            "UPDATE persistent_goals SET status = 'abandoned', evidence = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_evidence, row["id"]),
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


    def ranked_open_goals(self, limit: int = 20) -> list[dict[str, Any]]:
        """List actionable goals by priority, then lower completion, then age.

        Paused goals are excluded: they require an explicit resume operation.
        Goals needing revision remain visible but rank below active goals at
        equal priority so unresolved failures do not silently dominate.
        """
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._db.execute(
            "SELECT * FROM persistent_goals WHERE status IN "
            "('active', 'needs_revision') "
            "ORDER BY priority DESC, "
            "CASE status WHEN 'active' THEN 0 ELSE 1 END ASC, "
            "progress ASC, id ASC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._as_dict(row) for row in rows]

    def record_deliberation(
        self,
        *,
        selected_goal_id: str | None,
        selected_source: str | None,
        rationale: str,
        alternatives: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> int:
        """Persist one deliberation and its evidence for continuity across restarts."""
        if selected_goal_id is not None and (not isinstance(selected_goal_id, str) or not selected_goal_id.strip()):
            raise ValueError("selected_goal_id must be a non-empty string or None")
        if selected_source not in {None, "generated", "persistent"}:
            raise ValueError("selected_source must be generated, persistent, or None")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("rationale must be non-empty")
        if not isinstance(alternatives, list) or not isinstance(context, dict):
            raise ValueError("alternatives and context must be a list and dictionary")
        cursor = self._db.execute(
            "INSERT INTO deliberation_history "
            "(selected_goal_id, selected_source, rationale, alternatives_json, context_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                selected_goal_id,
                selected_source,
                rationale,
                json.dumps(alternatives, ensure_ascii=False, sort_keys=True),
                json.dumps(context, ensure_ascii=False, sort_keys=True),
            ),
        )
        self._db.commit()
        return int(cursor.lastrowid)

    def recent_deliberations(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return newest deliberations with decoded, inspectable evidence."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._db.execute(
            "SELECT * FROM deliberation_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["alternatives"] = json.loads(item.pop("alternatives_json"))
            item["context"] = json.loads(item.pop("context_json"))
            result.append(item)
        return result


    def record_plan_revision(
        self,
        *,
        previous_goal_ids: list[str],
        selected_goal_ids: list[str],
        deferred_goal_ids: list[str],
        trigger: str,
        rationale: str,
        context: dict[str, Any] | None = None,
    ) -> int:
        """Append an auditable plan comparison; does not alter goal lifecycle."""
        values = (previous_goal_ids, selected_goal_ids, deferred_goal_ids)
        if any(not isinstance(items, list) or any(
            not isinstance(item, str) or not item.strip() for item in items
        ) or len(set(items)) != len(items) for items in values):
            raise ValueError("plan goal IDs must be unique non-empty string lists")
        if not isinstance(trigger, str) or not trigger.strip():
            raise ValueError("plan revision trigger must be non-empty")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("plan revision rationale must be non-empty")
        if context is not None and not isinstance(context, dict):
            raise ValueError("plan revision context must be a dictionary")
        cursor = self._db.execute(
            "INSERT INTO plan_revision_history "
            "(previous_goal_ids_json, selected_goal_ids_json, deferred_goal_ids_json, "
            "trigger, rationale, context_json) VALUES (?, ?, ?, ?, ?, ?)",
            (
                json.dumps(previous_goal_ids, ensure_ascii=False),
                json.dumps(selected_goal_ids, ensure_ascii=False),
                json.dumps(deferred_goal_ids, ensure_ascii=False),
                trigger.strip(), rationale.strip(),
                json.dumps(context or {}, ensure_ascii=False, sort_keys=True),
            ),
        )
        self._db.commit()
        return int(cursor.lastrowid)

    def recent_plan_revisions(self, limit: int = 10) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._db.execute(
            "SELECT * FROM plan_revision_history ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            for key in ("previous_goal_ids", "selected_goal_ids", "deferred_goal_ids", "context"):
                column = key + "_json"
                item[key] = json.loads(item.pop(column))
            result.append(item)
        return result

    def add_goal_relation(
        self,
        source_goal_id: str,
        target_goal_id: str,
        relation: str,
        *,
        strength: float = 1.0,
        evidence: str,
    ) -> dict[str, Any]:
        """Persist an explicit, evidence-backed relation between goal types."""
        import math

        source = source_goal_id.strip() if isinstance(source_goal_id, str) else ""
        target = target_goal_id.strip() if isinstance(target_goal_id, str) else ""
        note = evidence.strip() if isinstance(evidence, str) else ""
        if not source or not target or source == target:
            raise ValueError("goal relations require two distinct non-empty goal IDs")
        if relation not in {"conflicts", "supports", "requires"}:
            raise ValueError("relation must be conflicts, supports, or requires")
        if isinstance(strength, bool) or not isinstance(strength, (int, float)) or not math.isfinite(strength) or not 0.0 <= strength <= 1.0:
            raise ValueError("strength must be finite and between 0 and 1")
        if not note:
            raise ValueError("goal relations require non-empty evidence")
        if relation == "conflicts":
            left, right = sorted((source, target))
            self._db.execute(
                "DELETE FROM goal_relations WHERE relation = 'conflicts' "
                "AND ((source_goal_id = ? AND target_goal_id = ?) "
                "OR (source_goal_id = ? AND target_goal_id = ?))",
                (left, right, right, left),
            )
            source, target = left, right
        self._db.execute(
            "INSERT INTO goal_relations "
            "(source_goal_id, target_goal_id, relation, strength, evidence) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(source_goal_id, target_goal_id, relation) DO UPDATE SET "
            "strength = excluded.strength, evidence = excluded.evidence",
            (source, target, relation, float(strength), note),
        )
        self._db.commit()
        row = self._db.execute(
            "SELECT * FROM goal_relations WHERE source_goal_id = ? "
            "AND target_goal_id = ? AND relation = ?",
            (source, target, relation),
        ).fetchone()
        return dict(row)

    def goal_relations(self, goal_id: str | None = None) -> list[dict[str, Any]]:
        """List explicit relations; conflict edges are stored in canonical order."""
        if goal_id is None:
            rows = self._db.execute(
                "SELECT * FROM goal_relations ORDER BY id ASC"
            ).fetchall()
        else:
            rows = self._db.execute(
                "SELECT * FROM goal_relations WHERE source_goal_id = ? "
                "OR target_goal_id = ? ORDER BY id ASC",
                (goal_id, goal_id),
            ).fetchall()
        return [dict(row) for row in rows]

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
