"""Persistent, inspectable strategy learning for Machina's adaptive-autonomy phase.

This is a small empirical-reward learner, not a general-purpose planner. It
chooses among supplied strategies per task type, records objective rewards, and
persists estimates in SQLite so later runs can reuse experience.
"""
from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Iterable


class AdaptiveStrategyLearner:
    """Select strategies by empirical mean reward, exploring unseen options first."""

    def __init__(self, database: str | Path) -> None:
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute(
            """
            CREATE TABLE IF NOT EXISTS strategy_outcomes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                reward REAL NOT NULL CHECK (reward >= 0.0 AND reward <= 1.0),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_strategy_outcomes_task "
            "ON strategy_outcomes(task_type, strategy)"
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _validate_label(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    def choose_strategy(self, task_type: str, strategies: Iterable[str]) -> str:
        """Explore untried strategies first; then choose the highest mean reward.

        Ties are deterministic: fewer observations first, then lexical strategy
        name. This makes experiments reproducible and avoids random test flakes.
        """
        task_type = self._validate_label(task_type, "task_type")
        options = sorted({self._validate_label(item, "strategy") for item in strategies})
        if not options:
            raise ValueError("at least one strategy is required")

        rows = self._db.execute(
            """
            SELECT strategy, COUNT(*) AS trials, AVG(reward) AS mean_reward
            FROM strategy_outcomes
            WHERE task_type = ?
            GROUP BY strategy
            """,
            (task_type,),
        ).fetchall()
        stats = {row["strategy"]: (int(row["trials"]), float(row["mean_reward"])) for row in rows}
        unseen = [option for option in options if option not in stats]
        if unseen:
            return min(unseen)

        # Lower trial count breaks close estimates toward additional evidence.
        return max(options, key=lambda option: (stats[option][1], -stats[option][0], option))

    def record_outcome(self, task_type: str, strategy: str, reward: float) -> None:
        """Store externally evaluated reward in [0, 1]."""
        task_type = self._validate_label(task_type, "task_type")
        strategy = self._validate_label(strategy, "strategy")
        if isinstance(reward, bool) or not isinstance(reward, (int, float)):
            raise ValueError("reward must be a finite number between 0 and 1")
        if not math.isfinite(reward) or not 0.0 <= reward <= 1.0:
            raise ValueError("reward must be a finite number between 0 and 1")
        self._db.execute(
            "INSERT INTO strategy_outcomes (task_type, strategy, reward) VALUES (?, ?, ?)",
            (task_type, strategy, float(reward)),
        )
        self._db.commit()

    def strategy_stats(self, task_type: str) -> dict[str, dict[str, float | int]]:
        """Return transparent trial counts and mean reward for one task type."""
        task_type = self._validate_label(task_type, "task_type")
        rows = self._db.execute(
            """
            SELECT strategy, COUNT(*) AS trials, AVG(reward) AS mean_reward
            FROM strategy_outcomes
            WHERE task_type = ?
            GROUP BY strategy ORDER BY strategy
            """,
            (task_type,),
        ).fetchall()
        return {
            row["strategy"]: {
                "trials": int(row["trials"]),
                "mean_reward": float(row["mean_reward"]),
            }
            for row in rows
        }

    def summary(self) -> dict[str, int | float]:
        row = self._db.execute(
            "SELECT COUNT(*) AS trials, COALESCE(AVG(reward), 0.0) AS mean_reward "
            "FROM strategy_outcomes"
        ).fetchone()
        return {"trials": int(row["trials"]), "mean_reward": float(row["mean_reward"])}
