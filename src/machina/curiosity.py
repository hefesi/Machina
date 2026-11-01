"""Persistent, append-only memory for curiosity investigations.

Questions and hypotheses are caller-authored. Evidence is stored separately
from interpretation and must carry an external reference supplied by the caller.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable


class CuriosityInvestigationStore:
    """SQLite-backed investigation lifecycle and evidence ledger.

    Investigation identity and evidence are durable across process restarts.
    Records are append-only: evidence cannot be edited/deleted and a closed
    investigation cannot be reopened or closed a second time.
    """

    OUTCOMES = {"answered", "partially_answered", "unanswered", "abandoned"}

    def __init__(self, database: str | Path) -> None:
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS curiosity_investigations (
                investigation_id TEXT PRIMARY KEY,
                gap_property TEXT NOT NULL,
                question TEXT NOT NULL,
                question_key TEXT NOT NULL,
                hypothesis TEXT NOT NULL,
                selection_reason TEXT NOT NULL,
                cycle_id TEXT NOT NULL,
                goal_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK (status IN ('open', 'closed')),
                outcome TEXT CHECK (outcome IS NULL OR outcome IN
                    ('answered','partially_answered','unanswered','abandoned')),
                answer_summary TEXT,
                remaining_unknowns TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                closed_at TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_curiosity_one_open_question
                ON curiosity_investigations(gap_property, question_key)
                WHERE status = 'open';
            CREATE INDEX IF NOT EXISTS idx_curiosity_question_history
                ON curiosity_investigations(gap_property, question_key, created_at);
            CREATE TABLE IF NOT EXISTS curiosity_evidence (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                investigation_id TEXT NOT NULL REFERENCES
                    curiosity_investigations(investigation_id),
                evidence_ref TEXT NOT NULL,
                finding TEXT NOT NULL,
                cycle_id TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(investigation_id, evidence_ref)
            );
            CREATE TABLE IF NOT EXISTS curiosity_reviews (
                review_id TEXT PRIMARY KEY,
                investigation_id TEXT NOT NULL REFERENCES curiosity_investigations(investigation_id),
                report TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS curiosity_closures (
                investigation_id TEXT PRIMARY KEY REFERENCES
                    curiosity_investigations(investigation_id),
                cycle_id TEXT NOT NULL,
                closed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _label(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _question_key(question: str) -> str:
        return " ".join(question.casefold().split())

    @staticmethod
    def _unknowns(values: Iterable[str]) -> list[str]:
        if isinstance(values, (str, bytes)):
            raise ValueError("remaining_unknowns must be an iterable of non-empty strings")
        try:
            result = [CuriosityInvestigationStore._label(item, "remaining unknown") for item in values]
        except TypeError as exc:
            raise ValueError("remaining_unknowns must be an iterable of non-empty strings") from exc
        if len(set(item.casefold() for item in result)) != len(result):
            raise ValueError("remaining_unknowns must not contain duplicates")
        return result

    def start_investigation(
        self,
        investigation_id: str,
        *,
        gap_property: str,
        question: str,
        hypothesis: str,
        selection_reason: str,
        cycle_id: str,
        goal_id: str,
    ) -> dict[str, Any]:
        key = self._label(investigation_id, "investigation_id")
        prop = self._label(gap_property, "gap_property")
        prompt = self._label(question, "question")
        theory = self._label(hypothesis, "hypothesis")
        reason = self._label(selection_reason, "selection_reason")
        cycle = self._label(cycle_id, "cycle_id")
        goal = self._label(goal_id, "goal_id")
        try:
            self._db.execute(
                """INSERT INTO curiosity_investigations
                (investigation_id, gap_property, question, question_key,
                 hypothesis, selection_reason, cycle_id, goal_id, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
                (key, prop, prompt, self._question_key(prompt), theory, reason, cycle, goal),
            )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            raise ValueError(
                "investigation_id already exists or an equivalent question is already open"
            ) from exc
        return self.get_investigation(key)

    def record_evidence(
        self,
        investigation_id: str,
        *,
        evidence_ref: str,
        finding: str,
        cycle_id: str,
    ) -> dict[str, Any]:
        key = self._label(investigation_id, "investigation_id")
        ref = self._label(evidence_ref, "evidence_ref")
        note = self._label(finding, "finding")
        cycle = self._label(cycle_id, "cycle_id")
        investigation = self.get_investigation(key)
        if investigation["status"] != "open":
            raise ValueError("cannot add evidence to a closed investigation")
        try:
            cursor = self._db.execute(
                """INSERT INTO curiosity_evidence
                (investigation_id, evidence_ref, finding, cycle_id)
                VALUES (?, ?, ?, ?)""",
                (key, ref, note, cycle),
            )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            raise ValueError("evidence_ref has already been recorded for this investigation") from exc
        return {
            "record_id": int(cursor.lastrowid), "investigation_id": key,
            "evidence_ref": ref, "finding": note, "cycle_id": cycle,
        }

    def close_investigation(
        self,
        investigation_id: str,
        *,
        outcome: str,
        answer_summary: str,
        remaining_unknowns: Iterable[str],
        cycle_id: str,
    ) -> dict[str, Any]:
        key = self._label(investigation_id, "investigation_id")
        result = self._label(outcome, "outcome")
        if result not in self.OUTCOMES:
            raise ValueError("outcome must be answered, partially_answered, unanswered, or abandoned")
        summary = self._label(answer_summary, "answer_summary")
        unknowns = self._unknowns(remaining_unknowns)
        cycle = self._label(cycle_id, "cycle_id")
        cursor = self._db.execute(
            """UPDATE curiosity_investigations
            SET status='closed', outcome=?, answer_summary=?,
                remaining_unknowns=?, closed_at=CURRENT_TIMESTAMP
            WHERE investigation_id=? AND status='open'""",
            (result, summary, json.dumps(unknowns, ensure_ascii=False), key),
        )
        if cursor.rowcount != 1:
            self._db.rollback()
            if self._db.execute(
                "SELECT 1 FROM curiosity_investigations WHERE investigation_id=?", (key,)
            ).fetchone() is None:
                raise ValueError("unknown investigation_id")
            raise ValueError("investigation is already closed")
        # Record the closing cycle in a dedicated immutable lifecycle event.
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS curiosity_closures (
                investigation_id TEXT PRIMARY KEY REFERENCES
                    curiosity_investigations(investigation_id),
                cycle_id TEXT NOT NULL,
                closed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        self._db.execute(
            "INSERT INTO curiosity_closures (investigation_id, cycle_id) VALUES (?, ?)",
            (key, cycle),
        )
        self._db.commit()
        return self.get_investigation(key)

    def record_review(self, review_id: str, investigation_id: str, report: dict[str, Any]) -> dict[str, Any]:
        """Persist one immutable assessment report per caller-supplied review ID."""
        review = self._label(review_id, "review_id")
        key = self._label(investigation_id, "investigation_id")
        self.get_investigation(key)
        if not isinstance(report, dict):
            raise ValueError("report must be a mapping")
        payload = json.dumps(report, ensure_ascii=False, sort_keys=True, allow_nan=False)
        try:
            self._db.execute(
                "INSERT INTO curiosity_reviews (review_id, investigation_id, report) VALUES (?, ?, ?)",
                (review, key, payload),
            )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            raise ValueError("review_id already exists") from exc
        return self.get_review(review)

    def get_review(self, review_id: str) -> dict[str, Any]:
        review = self._label(review_id, "review_id")
        row = self._db.execute(
            "SELECT review_id, investigation_id, report, created_at FROM curiosity_reviews WHERE review_id=?",
            (review,),
        ).fetchone()
        if row is None:
            raise ValueError("unknown review_id")
        result = dict(row)
        result["report"] = json.loads(result["report"])
        return result

    def find_review(self, review_id: str) -> dict[str, Any] | None:
        review = self._label(review_id, "review_id")
        row = self._db.execute("SELECT 1 FROM curiosity_reviews WHERE review_id=?", (review,)).fetchone()
        return self.get_review(review) if row else None

    def get_investigation(self, investigation_id: str) -> dict[str, Any]:
        key = self._label(investigation_id, "investigation_id")
        row = self._db.execute(
            "SELECT * FROM curiosity_investigations WHERE investigation_id=?", (key,)
        ).fetchone()
        if row is None:
            raise ValueError("unknown investigation_id")
        result = dict(row)
        result["remaining_unknowns"] = json.loads(result["remaining_unknowns"])
        result["evidence"] = [
            dict(item) for item in self._db.execute(
                "SELECT record_id, evidence_ref, finding, cycle_id, created_at "
                "FROM curiosity_evidence WHERE investigation_id=? ORDER BY record_id",
                (key,),
            ).fetchall()
        ]
        closure = self._db.execute(
            "SELECT cycle_id FROM curiosity_closures WHERE investigation_id=?", (key,)
        ).fetchone()
        result["closed_cycle_id"] = closure["cycle_id"] if closure else None
        return result

    def open_investigations(self) -> list[dict[str, Any]]:
        """Return all open investigations in creation order for goal generation."""
        rows = self._db.execute(
            "SELECT investigation_id FROM curiosity_investigations "
            "WHERE status='open' ORDER BY rowid"
        ).fetchall()
        return [self.get_investigation(row["investigation_id"]) for row in rows]

    def history(self, *, gap_property: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT investigation_id FROM curiosity_investigations"
        params: tuple[Any, ...] = ()
        if gap_property is not None:
            query += " WHERE gap_property=?"
            params = (self._label(gap_property, "gap_property"),)
        query += " ORDER BY rowid"
        return [self.get_investigation(row["investigation_id"])
                for row in self._db.execute(query, params).fetchall()]

    def has_prior_question(self, gap_property: str, question: str) -> bool:
        prop = self._label(gap_property, "gap_property")
        prompt = self._label(question, "question")
        row = self._db.execute(
            """SELECT 1 FROM curiosity_investigations
            WHERE gap_property=? AND question_key=? LIMIT 1""",
            (prop, self._question_key(prompt)),
        ).fetchone()
        return row is not None

    def has_open_question(self, gap_property: str, question: str) -> bool:
        prop = self._label(gap_property, "gap_property")
        prompt = self._label(question, "question")
        row = self._db.execute(
            """SELECT 1 FROM curiosity_investigations
            WHERE gap_property=? AND question_key=? AND status='open' LIMIT 1""",
            (prop, self._question_key(prompt)),
        ).fetchone()
        return row is not None
