"""Durable, evidence-backed memory of the agent's own experiences.

Intentions are recorded before execution; outcomes are appended later by an
explicit evaluator. Strategy summaries are descriptive recommendations, not
automatic policy changes or evidence of consciousness.
"""
from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any


class ExperienceMemoryStore:
    """Append-only intent/outcome ledger with cautious strategy comparisons."""

    def __init__(self, database: str | Path) -> None:
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS agent_experiences (
                experience_id TEXT PRIMARY KEY,
                cycle_id TEXT NOT NULL,
                goal_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                intention TEXT NOT NULL,
                expected_outcome REAL,
                context_ref TEXT,
                prediction_ref TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS agent_experience_outcomes (
                outcome_id TEXT PRIMARY KEY,
                experience_id TEXT NOT NULL UNIQUE
                    REFERENCES agent_experiences(experience_id),
                observed_outcome REAL NOT NULL
                    CHECK(observed_outcome >= 0.0 AND observed_outcome <= 1.0),
                evidence_ref TEXT NOT NULL,
                evaluator TEXT NOT NULL,
                note TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_experience_strategy "
            "ON agent_experiences(strategy, experience_id)"
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _text(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _score(value: float | None, name: str, *, optional: bool = False) -> float | None:
        if value is None and optional:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be finite and in [0, 1]")
        number = float(value)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise ValueError(f"{name} must be finite and in [0, 1]")
        return number

    def begin(
        self, experience_id: str, *, cycle_id: str, goal_id: str,
        strategy: str, intention: str, expected_outcome: float | None = None,
        context_ref: str | None = None, prediction_ref: str | None = None,
    ) -> dict[str, Any]:
        """Persist what the agent intends to do, before any execution occurs."""
        token = self._text(experience_id, "experience_id")
        cycle = self._text(cycle_id, "cycle_id")
        goal = self._text(goal_id, "goal_id")
        method = self._text(strategy, "strategy")
        intent = self._text(intention, "intention")
        expected = self._score(expected_outcome, "expected_outcome", optional=True)
        context = None if context_ref is None else self._text(context_ref, "context_ref")
        prediction = None if prediction_ref is None else self._text(prediction_ref, "prediction_ref")
        values = (cycle, goal, method, intent, expected, context, prediction)
        existing = self._db.execute(
            "SELECT cycle_id, goal_id, strategy, intention, expected_outcome, context_ref, prediction_ref "
            "FROM agent_experiences WHERE experience_id = ?", (token,)
        ).fetchone()
        if existing is not None:
            if tuple(existing) != values:
                raise ValueError("experience_id already exists with different intent")
            return {**dict(existing), "experience_id": token, "already_recorded": True}
        self._db.execute(
            "INSERT INTO agent_experiences "
            "(experience_id, cycle_id, goal_id, strategy, intention, expected_outcome, context_ref, prediction_ref) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (token, *values)
        )
        self._db.commit()
        return {"experience_id": token, "cycle_id": cycle, "goal_id": goal,
                "strategy": method, "intention": intent, "expected_outcome": expected,
                "context_ref": context, "prediction_ref": prediction, "already_recorded": False}

    def record_outcome(
        self, experience_id: str, *, outcome_id: str, observed_outcome: float,
        evidence_ref: str, evaluator: str, note: str,
    ) -> dict[str, Any]:
        """Append an externally evaluated outcome; never infer success from prose."""
        token = self._text(experience_id, "experience_id")
        outcome_token = self._text(outcome_id, "outcome_id")
        score = self._score(observed_outcome, "observed_outcome")
        evidence = self._text(evidence_ref, "evidence_ref")
        source = self._text(evaluator, "evaluator")
        rationale = self._text(note, "note")
        intent = self._db.execute(
            "SELECT * FROM agent_experiences WHERE experience_id = ?", (token,)
        ).fetchone()
        if intent is None:
            raise ValueError("experience must be recorded before its outcome")
        existing = self._db.execute(
            "SELECT * FROM agent_experience_outcomes WHERE experience_id = ?", (token,)
        ).fetchone()
        if existing is not None:
            same = (existing["outcome_id"], existing["observed_outcome"],
                    existing["evidence_ref"], existing["evaluator"], existing["note"])
            if same != (outcome_token, score, evidence, source, rationale):
                raise ValueError("experience already has a different outcome")
            return {**dict(existing), "already_recorded": True}
        duplicate = self._db.execute(
            "SELECT experience_id FROM agent_experience_outcomes WHERE outcome_id = ?",
            (outcome_token,)
        ).fetchone()
        if duplicate is not None:
            raise ValueError("outcome_id has already been used")
        self._db.execute(
            "INSERT INTO agent_experience_outcomes "
            "(outcome_id, experience_id, observed_outcome, evidence_ref, evaluator, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (outcome_token, token, score, evidence, source, rationale)
        )
        self._db.commit()
        expected = intent["expected_outcome"]
        return {
            "outcome_id": outcome_token, "experience_id": token,
            "expected_outcome": expected, "observed_outcome": score,
            "prediction_error": None if expected is None else score - expected,
            "evidence_ref": evidence, "evaluator": source, "note": rationale,
            "already_recorded": False,
        }

    def get(self, experience_id: str) -> dict[str, Any]:
        token = self._text(experience_id, "experience_id")
        row = self._db.execute("""
            SELECT i.*, o.outcome_id, o.observed_outcome, o.evidence_ref,
                   o.evaluator, o.note AS outcome_note, o.created_at AS outcome_at
            FROM agent_experiences i
            LEFT JOIN agent_experience_outcomes o USING(experience_id)
            WHERE i.experience_id = ?
        """, (token,)).fetchone()
        if row is None:
            raise KeyError(token)
        result = dict(row)
        expected, observed = result["expected_outcome"], result["observed_outcome"]
        result["prediction_error"] = (
            None if expected is None or observed is None else observed - expected
        )
        result["evaluated"] = observed is not None
        return result

    def history(self, *, strategy: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        query = """
            SELECT i.*, o.outcome_id, o.observed_outcome, o.evidence_ref,
                   o.evaluator, o.note AS outcome_note
            FROM agent_experiences i
            LEFT JOIN agent_experience_outcomes o USING(experience_id)
        """
        params: tuple[Any, ...] = ()
        if strategy is not None:
            query += " WHERE i.strategy = ?"
            params = (self._text(strategy, "strategy"),)
        query += " ORDER BY i.rowid DESC LIMIT ?"
        rows = self._db.execute(query, (*params, limit)).fetchall()
        return [dict(row) for row in rows]

    def autobiographical_report(
        self, *, minimum_repetitions: int = 2, error_threshold: float = 0.15,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Summarize recorded history and repeated numeric prediction patterns."""
        if isinstance(minimum_repetitions, bool) or not isinstance(minimum_repetitions, int) or minimum_repetitions < 2:
            raise ValueError("minimum_repetitions must be an integer >= 2")
        threshold = self._score(error_threshold, "error_threshold")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._db.execute("""
            SELECT i.*, o.outcome_id, o.observed_outcome, o.evidence_ref,
                   o.evaluator, o.note AS outcome_note
            FROM agent_experiences i
            LEFT JOIN agent_experience_outcomes o USING(experience_id)
            WHERE i.rowid IN (
                SELECT rowid FROM agent_experiences ORDER BY rowid DESC LIMIT ?
            )
            ORDER BY i.rowid ASC
        """, (limit,)).fetchall()
        episodes = []
        groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in rows:
            item = dict(row)
            expected, observed = item["expected_outcome"], item["observed_outcome"]
            error = None if expected is None or observed is None else float(observed) - float(expected)
            episodes.append({
                "experience_id": item["experience_id"], "cycle_id": item["cycle_id"],
                "goal_id": item["goal_id"], "strategy": item["strategy"],
                "intention": item["intention"], "expected_outcome": expected,
                "observed_outcome": observed, "prediction_error": error,
                "evidence_ref": item["evidence_ref"], "evaluator": item["evaluator"],
                "status": "evaluated" if observed is not None else "pending_outcome",
            })
            if error is not None:
                groups.setdefault((item["goal_id"], item["strategy"]), []).append({
                    "experience_id": item["experience_id"], "error": error,
                    "evidence_ref": item["evidence_ref"],
                })
        patterns = []
        for (goal_id, strategy), observations in sorted(groups.items()):
            if len(observations) < minimum_repetitions:
                continue
            mean_error = sum(item["error"] for item in observations) / len(observations)
            if mean_error <= -threshold:
                pattern = "repeated_underestimation"
            elif mean_error >= threshold:
                pattern = "repeated_overestimation"
            else:
                pattern = "no_consistent_direction_detected"
            patterns.append({
                "goal_id": goal_id, "strategy": strategy, "pattern": pattern,
                "repetitions": len(observations),
                "mean_signed_prediction_error": mean_error,
                "mean_absolute_prediction_error": sum(abs(item["error"]) for item in observations) / len(observations),
                "experience_ids": [item["experience_id"] for item in observations],
                "evidence_refs": [item["evidence_ref"] for item in observations],
                "interpretation": "repeated_descriptive_pattern_not_causal",
            })
        return {
            "episodes": episodes, "patterns": patterns, "episodes_included": len(episodes),
            "minimum_repetitions": minimum_repetitions, "error_threshold": threshold,
            "chronology": "recorded_intention_order", "recommendation_only": True,
            "self_model_changed": False, "autonomy_policy_changed": False,
            "limitations": [
                "Only the most recent limit recorded intentions are included.",
                "Patterns require explicit numeric expectations and evaluator-scored outcomes.",
                "Grouping uses exact goal and strategy labels supplied by the caller.",
                "Repeated error direction is descriptive; context confounding is not resolved.",
                "No motives, feelings, subjective experience, or causal explanations are inferred.",
            ],
        }

    def strategy_report(
        self, *, minimum_samples: int = 3, minimum_difference: float = 0.1,
    ) -> dict[str, Any]:
        """Compare evaluated strategy means; report patterns, never change policy."""
        if isinstance(minimum_samples, bool) or not isinstance(minimum_samples, int) or minimum_samples < 2:
            raise ValueError("minimum_samples must be an integer >= 2")
        threshold = self._score(minimum_difference, "minimum_difference")
        rows = self._db.execute("""
            SELECT i.strategy, COUNT(*) AS n, AVG(o.observed_outcome) AS mean,
                   AVG((o.observed_outcome - i.expected_outcome) *
                       (o.observed_outcome - i.expected_outcome)) AS prediction_mse,
                   COUNT(i.expected_outcome) AS with_expectation
            FROM agent_experiences i
            JOIN agent_experience_outcomes o USING(experience_id)
            GROUP BY i.strategy ORDER BY i.strategy
        """).fetchall()
        strategies = {
            row["strategy"]: {
                "observations": int(row["n"]), "mean_outcome": float(row["mean"]),
                "prediction_mse": None if row["with_expectation"] == 0 else float(row["prediction_mse"]),
                "sufficient_sample": int(row["n"]) >= minimum_samples,
            } for row in rows
        }
        eligible = [(name, data) for name, data in strategies.items()
                    if data["sufficient_sample"]]
        comparisons = []
        for index, (left_name, left) in enumerate(eligible):
            for right_name, right in eligible[index + 1:]:
                difference = left["mean_outcome"] - right["mean_outcome"]
                comparisons.append({
                    "strategy_a": left_name, "strategy_b": right_name,
                    "mean_difference_a_minus_b": difference,
                    "descriptive_signal": abs(difference) >= threshold,
                    "interpretation": "observational_comparison_not_causal",
                })
        return {
            "strategies": strategies, "comparisons": comparisons,
            "minimum_samples": minimum_samples, "minimum_difference": threshold,
            "recommendation_only": True, "policy_changed": False,
            "execution_performed": False,
            "limitations": [
                "Outcomes and evidence are supplied by the evaluator.",
                "Strategy comparisons are observational and may be confounded by context.",
                "A descriptive difference does not establish causal effectiveness.",
            ],
        }
