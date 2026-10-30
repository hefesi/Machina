"""Empirical prediction of goal outcomes from Machina's own history.

Predictions are bounded estimates, not facts. Outcomes and evidence are
supplied by an evaluator; every update stores the prediction that preceded it.
"""
from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any


class GoalOutcomeLearner:
    """Learn goal-type outcome probabilities with a transparent Beta prior."""

    def __init__(
        self,
        database: str | Path,
        *,
        prior_success: float = 1.0,
        prior_failure: float = 1.0,
    ) -> None:
        for value, name in ((prior_success, "prior_success"), (prior_failure, "prior_failure")):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        self.prior_success = float(prior_success)
        self.prior_failure = float(prior_failure)
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS goal_outcome_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_type TEXT NOT NULL,
                outcome REAL NOT NULL CHECK (outcome >= 0.0 AND outcome <= 1.0),
                prediction_before REAL NOT NULL CHECK (prediction_before >= 0.0 AND prediction_before <= 1.0),
                prediction_error REAL NOT NULL,
                evidence TEXT NOT NULL,
                observation_id TEXT UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_goal_outcome_type "
            "ON goal_outcome_observations(goal_type, id)"
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _label(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    def predict(self, goal_type: str) -> dict[str, float | int]:
        """Return posterior mean, uncertainty, and evidence count."""
        label = self._label(goal_type, "goal_type")
        row = self._db.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(outcome), 0.0) AS successes "
            "FROM goal_outcome_observations WHERE goal_type = ?", (label,)
        ).fetchone()
        failures = int(row["n"]) - float(row["successes"])
        alpha = self.prior_success + float(row["successes"])
        beta = self.prior_failure + failures
        total = alpha + beta
        mean = alpha / total
        variance = (alpha * beta) / (total * total * (total + 1.0))
        return {
            "goal_type": label,
            "predicted_outcome": mean,
            "uncertainty": math.sqrt(variance),
            "observations": int(row["n"]),
        }

    def utility_estimates(self, goal_types: list[str] | tuple[str, ...]) -> dict[str, float]:
        """Provide posterior means in the utility format accepted by the scheduler."""
        labels = [self._label(item, "goal_type") for item in goal_types]
        if not labels or len(set(labels)) != len(labels):
            raise ValueError("goal_types must contain unique non-empty labels")
        return {
            label: float(self.predict(label)["predicted_outcome"])
            for label in labels
        }

    def observe(
        self,
        goal_type: str,
        outcome: float,
        *,
        evidence: str,
        observation_id: str | None = None,
    ) -> dict[str, Any]:
        """Compare an observed [0,1] outcome with its pre-update prediction."""
        label = self._label(goal_type, "goal_type")
        if isinstance(outcome, bool) or not isinstance(outcome, (int, float)) or not math.isfinite(outcome) or not 0.0 <= outcome <= 1.0:
            raise ValueError("outcome must be finite and between 0 and 1")
        note = self._label(evidence, "evidence")
        token = None if observation_id is None else self._label(observation_id, "observation_id")
        prediction = self.predict(label)
        expected = float(prediction["predicted_outcome"])
        error = float(outcome) - expected
        try:
            cursor = self._db.execute(
                "INSERT INTO goal_outcome_observations "
                "(goal_type, outcome, prediction_before, prediction_error, evidence, observation_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (label, float(outcome), expected, error, note, token),
            )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            raise ValueError("observation_id has already been recorded") from exc
        return {
            "record_id": int(cursor.lastrowid),
            "goal_type": label,
            "prediction_before": expected,
            "observed_outcome": float(outcome),
            "prediction_error": error,
            "squared_error": error * error,
            "prediction_after": self.predict(label),
            "evidence": note,
            "observation_id": token,
        }

    def history(self, goal_type: str, limit: int = 20) -> list[dict[str, Any]]:
        label = self._label(goal_type, "goal_type")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._db.execute(
            "SELECT * FROM goal_outcome_observations WHERE goal_type = ? "
            "ORDER BY id DESC LIMIT ?", (label, limit)
        ).fetchall()
        return [dict(row) for row in rows]
