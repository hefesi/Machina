"""Evidence-bounded causal experiments for internal decision learning.

The module distinguishes randomized and matched comparisons from observational
associations. It estimates group-level effects only; an individual's unobserved
counterfactual is never presented as known.
"""
from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any


class CausalExperimentStore:
    """Append-only experiment registry and outcome ledger.

    A randomized design requires an externally supplied protocol reference.
    The store records that declaration but cannot verify that randomization
    was actually performed or that the protocol was followed.
    """

    DESIGNS = {"randomized", "matched", "observational"}
    ARMS = {"treatment", "control"}

    def __init__(self, database: str | Path) -> None:
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS causal_experiments (
                experiment_id TEXT PRIMARY KEY,
                design TEXT NOT NULL CHECK (design IN ('randomized','matched','observational')),
                treatment_name TEXT NOT NULL,
                control_name TEXT NOT NULL,
                protocol_ref TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS causal_trials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL REFERENCES causal_experiments(experiment_id),
                arm TEXT NOT NULL CHECK (arm IN ('treatment','control')),
                outcome REAL NOT NULL CHECK (outcome >= 0.0 AND outcome <= 1.0),
                evidence_ref TEXT NOT NULL,
                context_key TEXT,
                trial_id TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_causal_trials_experiment "
            "ON causal_trials(experiment_id, arm, id)"
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _label(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    def register_experiment(
        self,
        experiment_id: str,
        *,
        design: str,
        treatment_name: str,
        control_name: str,
        protocol_ref: str,
    ) -> dict[str, Any]:
        key = self._label(experiment_id, "experiment_id")
        kind = self._label(design, "design")
        if kind not in self.DESIGNS:
            raise ValueError("design must be randomized, matched, or observational")
        treatment = self._label(treatment_name, "treatment_name")
        control = self._label(control_name, "control_name")
        protocol = self._label(protocol_ref, "protocol_ref")
        if treatment == control:
            raise ValueError("treatment_name and control_name must differ")
        if kind == "randomized" and not protocol:
            raise ValueError("randomized experiments require protocol_ref")
        try:
            self._db.execute(
                "INSERT INTO causal_experiments "
                "(experiment_id, design, treatment_name, control_name, protocol_ref) "
                "VALUES (?, ?, ?, ?, ?)",
                (key, kind, treatment, control, protocol),
            )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            raise ValueError("experiment_id has already been registered") from exc
        return self.experiment(key)

    def experiment(self, experiment_id: str) -> dict[str, Any]:
        key = self._label(experiment_id, "experiment_id")
        row = self._db.execute(
            "SELECT * FROM causal_experiments WHERE experiment_id = ?", (key,)
        ).fetchone()
        if row is None:
            raise ValueError("unknown experiment_id")
        return dict(row)

    def record_trial(
        self,
        experiment_id: str,
        arm: str,
        outcome: float,
        *,
        evidence_ref: str,
        trial_id: str,
        context_key: str | None = None,
    ) -> dict[str, Any]:
        key = self._label(experiment_id, "experiment_id")
        group = self._label(arm, "arm")
        if group not in self.ARMS:
            raise ValueError("arm must be treatment or control")
        if isinstance(outcome, bool) or not isinstance(outcome, (int, float)) or not math.isfinite(outcome) or not 0.0 <= outcome <= 1.0:
            raise ValueError("outcome must be finite and between 0 and 1")
        evidence = self._label(evidence_ref, "evidence_ref")
        token = self._label(trial_id, "trial_id")
        experiment = self.experiment(key)
        context = None if context_key is None else self._label(context_key, "context_key")
        if experiment["design"] == "matched" and context is None:
            raise ValueError("matched trials require context_key")
        if experiment["design"] != "matched" and context is not None:
            raise ValueError("context_key is only valid for matched experiments")
        if experiment["design"] == "matched":
            duplicate = self._db.execute(
                "SELECT 1 FROM causal_trials WHERE experiment_id = ? AND arm = ? AND context_key = ?",
                (key, group, context),
            ).fetchone()
            if duplicate:
                raise ValueError("matched context already has an observation for this arm")
        try:
            cursor = self._db.execute(
                "INSERT INTO causal_trials "
                "(experiment_id, arm, outcome, evidence_ref, context_key, trial_id) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (key, group, float(outcome), evidence, context, token),
            )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            raise ValueError("trial_id has already been recorded") from exc
        return {
            "record_id": int(cursor.lastrowid), "experiment_id": key,
            "arm": group, "outcome": float(outcome), "evidence_ref": evidence,
            "context_key": context, "trial_id": token,
        }

    def record_strategy_outcome(
        self,
        experiment_id: str,
        arm: str,
        outcome_event: object,
        *,
        context_key: str | None = None,
    ) -> dict[str, Any]:
        """Project one confirmed EventStore strategy outcome into this analysis ledger.

        EventStore remains authoritative. Replaying the same event is idempotent;
        a different payload reusing its operation ID is rejected.
        """
        event_type = getattr(outcome_event, "event_type", None)
        artifact = getattr(outcome_event, "artifact", None)
        cycle_id = getattr(outcome_event, "cycle_id", None)
        if event_type != "strategy.outcome.recorded" or artifact is None:
            raise ValueError("outcome_event must be a strategy.outcome.recorded event")
        if artifact.kind != "strategy_outcome":
            raise ValueError("outcome event must contain a strategy_outcome artifact")
        data = artifact.data
        if data.get("execution_confirmed") is not True:
            raise ValueError("strategy outcome must confirm execution")
        operation_id = self._label(data.get("operation_id"), "operation_id")
        observed = data.get("observed_reward")
        evidence = self._label(artifact.id, "evidence_ref")
        key = self._label(experiment_id, "experiment_id")
        group = self._label(arm, "arm")
        experiment = self.experiment(key)
        if experiment["design"] == "matched" and context_key is None:
            raise ValueError("matched strategy outcomes require context_key")
        if experiment["design"] != "matched" and context_key is not None:
            raise ValueError("context_key is only valid for matched experiments")
        trial_id = f"{key}:{operation_id}"
        existing = self._db.execute(
            "SELECT * FROM causal_trials WHERE trial_id = ?", (trial_id,)
        ).fetchone()
        expected_context = None if context_key is None else self._label(context_key, "context_key")
        if existing is not None:
            row = dict(existing)
            expected = (key, group, float(observed), evidence, expected_context)
            actual = (
                row["experiment_id"], row["arm"], row["outcome"],
                row["evidence_ref"], row["context_key"],
            )
            if actual != expected:
                raise ValueError("operation_id was already projected with different trial data")
            return row
        return self.record_trial(
            key, group, observed,
            evidence_ref=evidence,
            trial_id=trial_id,
            context_key=expected_context,
        )

    @staticmethod
    def _mean_variance(values: list[float]) -> tuple[float | None, float | None]:
        if not values:
            return None, None
        mean = sum(values) / len(values)
        if len(values) < 2:
            return mean, None
        variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
        return mean, variance

    def report(self, experiment_id: str, *, minimum_per_arm: int = 5) -> dict[str, Any]:
        key = self._label(experiment_id, "experiment_id")
        if isinstance(minimum_per_arm, bool) or not isinstance(minimum_per_arm, int) or minimum_per_arm < 2:
            raise ValueError("minimum_per_arm must be an integer >= 2")
        experiment = self.experiment(key)
        rows = self._db.execute(
            "SELECT arm, outcome, evidence_ref, context_key, trial_id "
            "FROM causal_trials WHERE experiment_id = ? ORDER BY id", (key,)
        ).fetchall()
        trials = [dict(row) for row in rows]
        treatment = [row["outcome"] for row in trials if row["arm"] == "treatment"]
        control = [row["outcome"] for row in trials if row["arm"] == "control"]
        treatment_mean, treatment_var = self._mean_variance(treatment)
        control_mean, control_var = self._mean_variance(control)
        counts_sufficient = len(treatment) >= minimum_per_arm and len(control) >= minimum_per_arm
        estimate: dict[str, Any] | None = None
        classification = "insufficient_evidence"
        if experiment["design"] == "observational":
            classification = "observational_association" if treatment and control else "insufficient_evidence"
        elif experiment["design"] == "matched":
            by_context: dict[str, dict[str, float]] = {}
            for row in trials:
                by_context.setdefault(row["context_key"], {})[row["arm"]] = row["outcome"]
            pairs = [arms for arms in by_context.values() if set(arms) == self.ARMS]
            differences = [pair["treatment"] - pair["control"] for pair in pairs]
            mean_diff, variance = self._mean_variance(differences)
            if len(pairs) >= minimum_per_arm:
                standard_error = math.sqrt(variance / len(pairs)) if variance is not None else None
                estimate = {
                    "effect": mean_diff, "standard_error": standard_error,
                    "confidence_interval_95_normal_approx": (
                        [mean_diff - 1.96 * standard_error, mean_diff + 1.96 * standard_error]
                        if standard_error is not None else None
                    ),
                    "matched_pairs": len(pairs),
                    "counterfactual_scope": "average paired contrast; not an individual counterfactual",
                }
                classification = "matched_comparison"
        elif counts_sufficient:
            difference = float(treatment_mean) - float(control_mean)
            standard_error = math.sqrt(
                float(treatment_var) / len(treatment) + float(control_var) / len(control)
            )
            estimate = {
                "effect": difference, "standard_error": standard_error,
                "confidence_interval_95_normal_approx": [
                    difference - 1.96 * standard_error,
                    difference + 1.96 * standard_error,
                ],
                "counterfactual_scope": "group-average contrast; not an individual counterfactual",
            }
            classification = "randomized_comparison"
        return {
            "experiment": experiment,
            "classification": classification,
            "treatment": {"n": len(treatment), "mean": treatment_mean},
            "control": {"n": len(control), "mean": control_mean},
            "estimate": estimate,
            "trials": trials,
            "limitations": [
                "The store records, but cannot verify, the declared assignment design.",
                "A confidence interval is an approximation and depends on design assumptions.",
                "Unmeasured confounding, interference, selection bias, and protocol violations may invalidate causal interpretation.",
                "The unobserved outcome for an individual unit is not directly knowable.",
            ],
        }


    def strategy_guidance(
        self,
        experiment_id: str,
        *,
        minimum_per_arm: int = 5,
    ) -> dict[str, Any]:
        """Return bounded decision support without mutating strategy policy.

        Only randomized or matched comparisons with an interval excluding zero
        can produce a directional recommendation. Observational associations,
        small samples, and inconclusive intervals always return hold.
        The caller remains responsible for policy approval and deployment.
        """
        report = self.report(experiment_id, minimum_per_arm=minimum_per_arm)
        estimate = report["estimate"]
        guidance = "hold"
        reason = "evidence_is_insufficient_or_not_identifying"
        interval = (
            estimate.get("confidence_interval_95_normal_approx")
            if isinstance(estimate, dict) else None
        )
        if report["classification"] == "observational_association":
            reason = "observational_data_cannot_authorize_policy_changes"
        elif isinstance(interval, list) and len(interval) == 2:
            lower, upper = interval
            if lower > 0:
                guidance = "favor_treatment_for_human_review"
                reason = "approximate_interval_is_above_zero"
            elif upper < 0:
                guidance = "favor_control_for_human_review"
                reason = "approximate_interval_is_below_zero"
            else:
                reason = "approximate_interval_includes_zero"
        return {
            "experiment_id": report["experiment"]["experiment_id"],
            "guidance": guidance,
            "reason": reason,
            "classification": report["classification"],
            "treatment": report["treatment"],
            "control": report["control"],
            "estimate": estimate,
            "policy_mutated": False,
            "requires_human_or_external_policy_approval": True,
            "limitations": list(report["limitations"]),
        }
