"""Hypothesis-driven, evidence-linked strategy self-review proposals.

The planner consumes evaluator-authored autobiographical summaries and caller-
authored hypotheses. An explicitly approved proposal can be registered as a
causal experiment, but registration never runs trials or changes policy.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Mapping


class StrategySelfReviewStore:
    """Append-only ledger for strategy hypotheses and human decisions."""

    def __init__(self, database: str | Path) -> None:
        self.path = Path(database)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(self.path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS strategy_review_proposals (
                proposal_id TEXT PRIMARY KEY,
                goal_id TEXT NOT NULL,
                strategy TEXT NOT NULL,
                alternative_strategy TEXT NOT NULL,
                hypothesis TEXT NOT NULL,
                rationale TEXT NOT NULL,
                outcome_metric TEXT NOT NULL,
                evidence_refs_json TEXT NOT NULL,
                confounders_json TEXT NOT NULL,
                source_pattern_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS strategy_review_decisions (
                decision_id TEXT PRIMARY KEY,
                proposal_id TEXT NOT NULL REFERENCES strategy_review_proposals(proposal_id),
                decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
                rationale TEXT NOT NULL,
                authorization_ref TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS idx_strategy_review_decisions "
            "ON strategy_review_decisions(proposal_id, created_at)"
        )
        duplicate_decision = self._db.execute(
            """
            SELECT proposal_id, COUNT(*) AS decisions
            FROM strategy_review_decisions
            GROUP BY proposal_id
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        ).fetchone()
        if duplicate_decision is not None:
            self._db.rollback()
            self._db.close()
            raise RuntimeError(
                "strategy review ledger contains multiple final decisions for one proposal; "
                "resolve the conflicting historical decisions before opening it"
            )
        self._db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_strategy_review_decisions_proposal_unique "
            "ON strategy_review_decisions(proposal_id)"
        )
        self._db.execute("""
            CREATE TABLE IF NOT EXISTS strategy_review_experiments (
                proposal_id TEXT PRIMARY KEY REFERENCES strategy_review_proposals(proposal_id),
                experiment_id TEXT NOT NULL UNIQUE,
                design TEXT NOT NULL,
                protocol_ref TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    @staticmethod
    def _text(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _json(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def propose(
        self,
        proposal_id: str,
        *,
        autobiographical_report: Mapping[str, Any],
        goal_id: str,
        strategy: str,
        alternative_strategy: str,
        hypothesis: str,
        rationale: str,
        outcome_metric: str,
        confounders: list[str] | tuple[str, ...],
        minimum_repetitions: int = 3,
    ) -> dict[str, Any]:
        """Persist a caller-authored hypothesis grounded in an existing pattern.

        The report is descriptive only. A proposal requires its evidence refs
        to be present in that report; no causal explanation is generated here.
        """
        key = self._text(proposal_id, "proposal_id")
        goal = self._text(goal_id, "goal_id")
        method = self._text(strategy, "strategy")
        alternative = self._text(alternative_strategy, "alternative_strategy")
        claim = self._text(hypothesis, "hypothesis")
        why = self._text(rationale, "rationale")
        metric = self._text(outcome_metric, "outcome_metric")
        if method == alternative:
            raise ValueError("alternative_strategy must differ from strategy")
        if isinstance(minimum_repetitions, bool) or not isinstance(minimum_repetitions, int) or minimum_repetitions < 2:
            raise ValueError("minimum_repetitions must be an integer >= 2")
        if not isinstance(autobiographical_report, Mapping):
            raise ValueError("autobiographical_report must be a mapping")
        if not isinstance(confounders, (list, tuple)) or not confounders:
            raise ValueError("confounders must contain at least one explicit limitation")
        normalized_confounders = [self._text(item, "confounder") for item in confounders]
        if len(set(normalized_confounders)) != len(normalized_confounders):
            raise ValueError("confounders must be unique")
        patterns = autobiographical_report.get("patterns")
        if not isinstance(patterns, list):
            raise ValueError("autobiographical_report must contain patterns")
        matches = [
            item for item in patterns
            if isinstance(item, Mapping)
            and item.get("goal_id") == goal
            and item.get("strategy") == method
        ]
        if len(matches) != 1:
            raise ValueError("report must contain exactly one matching goal/strategy pattern")
        pattern = dict(matches[0])
        repetitions = pattern.get("repetitions")
        if isinstance(repetitions, bool) or not isinstance(repetitions, int) or repetitions < minimum_repetitions:
            raise ValueError("matching pattern does not meet minimum_repetitions")
        evidence_refs = pattern.get("evidence_refs")
        if not isinstance(evidence_refs, list) or not evidence_refs:
            raise ValueError("matching pattern must include evidence_refs")
        refs = [self._text(item, "evidence_ref") for item in evidence_refs]
        if len(set(refs)) != len(refs):
            raise ValueError("pattern evidence_refs must be unique")
        episodes = autobiographical_report.get("episodes")
        if not isinstance(episodes, list):
            raise ValueError("autobiographical_report must contain episodes")
        grounded_refs = {
            item.get("evidence_ref") for item in episodes
            if isinstance(item, Mapping)
            and item.get("goal_id") == goal
            and item.get("strategy") == method
            and item.get("status") == "evaluated"
            and isinstance(item.get("evidence_ref"), str)
        }
        if not set(refs).issubset(grounded_refs):
            raise ValueError("pattern evidence_refs must be grounded in evaluated matching episodes")
        if pattern.get("interpretation") != "repeated_descriptive_pattern_not_causal":
            raise ValueError("matching pattern must be explicitly descriptive and non-causal")
        if pattern.get("pattern") not in {
            "repeated_underestimation", "repeated_overestimation",
            "no_consistent_direction_detected",
        }:
            raise ValueError("matching pattern has an unsupported classification")
        values = (
            goal, method, alternative, claim, why, metric,
            self._json(refs), self._json(normalized_confounders), self._json(pattern),
        )
        existing = self._db.execute(
            "SELECT goal_id, strategy, alternative_strategy, hypothesis, rationale, "
            "outcome_metric, evidence_refs_json, confounders_json, source_pattern_json "
            "FROM strategy_review_proposals WHERE proposal_id = ?", (key,)
        ).fetchone()
        if existing is not None:
            if tuple(existing) != values:
                raise ValueError("proposal_id already exists with different content")
            return self.get(key) | {"already_recorded": True}
        self._db.execute(
            "INSERT INTO strategy_review_proposals "
            "(proposal_id, goal_id, strategy, alternative_strategy, hypothesis, rationale, "
            "outcome_metric, evidence_refs_json, confounders_json, source_pattern_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (key, *values),
        )
        self._db.commit()
        return self.get(key) | {"already_recorded": False}

    def decide(
        self,
        proposal_id: str,
        *,
        decision_id: str,
        decision: str,
        rationale: str,
        authorization_ref: str,
    ) -> dict[str, Any]:
        """Append an explicit approval/rejection; approval does not execute or apply."""
        key = self._text(proposal_id, "proposal_id")
        token = self._text(decision_id, "decision_id")
        choice = self._text(decision, "decision")
        if choice not in {"approved", "rejected"}:
            raise ValueError("decision must be approved or rejected")
        why = self._text(rationale, "rationale")
        authorization = self._text(authorization_ref, "authorization_ref")
        values = (key, choice, why, authorization)
        # Serialize the read/check/write sequence across independent SQLite
        # connections. The unique index below is the durable invariant; the
        # immediate transaction makes competing callers observe the winner.
        self._db.execute("BEGIN IMMEDIATE")
        try:
            self.get(key)
            existing = self._db.execute(
                "SELECT proposal_id, decision, rationale, authorization_ref "
                "FROM strategy_review_decisions WHERE decision_id = ?", (token,)
            ).fetchone()
            if existing is not None:
                if tuple(existing) != values:
                    raise ValueError("decision_id already exists with different content")
                self._db.commit()
                return self.get(key) | {"already_recorded": True}
            prior = self._db.execute(
                "SELECT decision FROM strategy_review_decisions "
                "WHERE proposal_id = ? LIMIT 1", (key,)
            ).fetchone()
            if prior is not None:
                raise ValueError("proposal already has a final decision")
            self._db.execute(
                "INSERT INTO strategy_review_decisions "
                "(decision_id, proposal_id, decision, rationale, authorization_ref) "
                "VALUES (?, ?, ?, ?, ?)", (token, *values)
            )
            self._db.commit()
            return self.get(key) | {"already_recorded": False}
        except Exception:
            self._db.rollback()
            raise

    def register_approved_experiment(
        self,
        proposal_id: str,
        causal_store: Any,
        *,
        experiment_id: str,
        design: str,
        protocol_ref: str,
    ) -> dict[str, Any]:
        """Register an approved alternative for a separately run comparison.

        The existing strategy is the control and the proposed alternative is
        the treatment. Approval is required before registration. This method
        creates only the experiment definition: it does not assign trials,
        execute strategies, infer a causal effect, or mutate policy.

        The review-to-experiment link is durable and idempotent. A write to
        the causal store that succeeds before a failed link write can be
        recovered on retry. An immediate transaction serializes concurrent
        registrations for the same review ledger.
        """
        from .causal_learning import CausalExperimentStore

        if not isinstance(causal_store, CausalExperimentStore):
            raise TypeError("causal_store must be a CausalExperimentStore")
        key = self._text(proposal_id, "proposal_id")
        experiment_key = self._text(experiment_id, "experiment_id")
        kind = self._text(design, "design")
        protocol = self._text(protocol_ref, "protocol_ref")

        # Lock the review ledger before checking the link. Without this,
        # independent callers can both observe an absent link, race to create
        # the causal definition, and turn an otherwise idempotent retry into
        # a duplicate-key error.
        self._db.execute("BEGIN IMMEDIATE")
        try:
            review = self.get(key)
            decision = review["decision"]
            if decision is None or decision["decision"] != "approved":
                raise ValueError("strategy proposal requires an explicit approved decision")

            proposal = review["proposal"]
            treatment = proposal["alternative_strategy"]
            control = proposal["strategy"]
            expected = (kind, treatment, control, protocol)

            linked = self._db.execute(
                "SELECT experiment_id, design, protocol_ref "
                "FROM strategy_review_experiments WHERE proposal_id = ?",
                (key,),
            ).fetchone()
            if linked is not None:
                if tuple(linked) != (experiment_key, kind, protocol):
                    raise ValueError("proposal is already linked to a different experiment")
                already_registered = True
            else:
                other_link = self._db.execute(
                    "SELECT proposal_id FROM strategy_review_experiments WHERE experiment_id = ?",
                    (experiment_key,),
                ).fetchone()
                if other_link is not None and other_link["proposal_id"] != key:
                    raise ValueError("experiment_id is already linked to another proposal")
                already_registered = False

            try:
                experiment = causal_store.experiment(experiment_key)
            except ValueError:
                experiment = causal_store.register_experiment(
                    experiment_key,
                    design=kind,
                    treatment_name=treatment,
                    control_name=control,
                    protocol_ref=protocol,
                )
            else:
                actual = (
                    experiment["design"], experiment["treatment_name"],
                    experiment["control_name"], experiment["protocol_ref"],
                )
                if actual != expected:
                    raise ValueError("experiment_id already exists with different configuration")
                already_registered = True

            if linked is None:
                self._db.execute(
                    "INSERT INTO strategy_review_experiments "
                    "(proposal_id, experiment_id, design, protocol_ref) "
                    "VALUES (?, ?, ?, ?)",
                    (key, experiment_key, kind, protocol),
                )
            self._db.commit()
        except sqlite3.IntegrityError as exc:
            self._db.rollback()
            raise ValueError("proposal or experiment is already linked") from exc
        except Exception:
            self._db.rollback()
            raise

        return {
            "proposal_id": key,
            "decision_id": decision["decision_id"],
            "authorization_ref": decision["authorization_ref"],
            "experiment": experiment,
            "already_registered": already_registered,
            "experiment_definition_created": not already_registered,
            "execution_performed": False,
            "policy_changed": False,
            "requires_separate_protocol_execution": True,
        }

    def get(self, proposal_id: str) -> dict[str, Any]:
        key = self._text(proposal_id, "proposal_id")
        row = self._db.execute(
            "SELECT * FROM strategy_review_proposals WHERE proposal_id = ?", (key,)
        ).fetchone()
        if row is None:
            raise KeyError(key)
        proposal = dict(row)
        for field, target in (
            ("evidence_refs_json", "evidence_refs"),
            ("confounders_json", "confounders"),
            ("source_pattern_json", "source_pattern"),
        ):
            proposal[target] = json.loads(proposal.pop(field))
        decision = self._db.execute(
            "SELECT decision_id, decision, rationale, authorization_ref, created_at "
            "FROM strategy_review_decisions WHERE proposal_id = ? ORDER BY rowid DESC LIMIT 1",
            (key,),
        ).fetchone()
        return {
            "proposal": proposal,
            "decision": None if decision is None else dict(decision),
            "status": "proposed" if decision is None else decision["decision"],
            "experiment_started": False,
            "policy_changed": False,
            "execution_performed": False,
        }

    def history(self, *, limit: int = 100) -> list[dict[str, Any]]:
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._db.execute(
            "SELECT proposal_id FROM strategy_review_proposals ORDER BY rowid DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self.get(row["proposal_id"]) for row in rows]
