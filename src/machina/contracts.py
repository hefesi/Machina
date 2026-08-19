"""Versioned data contracts for the Virtual Brain v0.1 loop.

The project documentation defines many named objects (Observation,
WorkspaceState, ActionIntent, Experience, and so on).  The implementation
uses a single immutable envelope for all of them.  That makes provenance,
causation, versioning and persistence mandatory instead of optional fields
that an individual component can forget to fill in.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
from typing import Any, Mapping, Sequence
from uuid import uuid4


SCHEMA_VERSION = "0.1"


class ContractError(ValueError):
    """Raised when an artifact does not satisfy its public contract."""


class ContractKind(StrEnum):
    OBSERVATION = "observation"
    GOAL = "goal"
    CYCLE_CONTEXT = "cycle_context"
    WORKSPACE_STATE = "workspace_state"
    MEMORY_QUERY = "memory_query"
    MEMORY_RETRIEVAL = "memory_retrieval"
    COGNITIVE_REQUEST = "cognitive_request"
    COGNITIVE_RESULT = "cognitive_result"
    DECISION_REQUEST = "decision_request"
    DECISION = "decision"
    ACTION_INTENT = "action_intent"
    ACTION_EXECUTION = "action_execution"
    ACTION_RESULT = "action_result"
    EXPERIENCE = "experience"
    MEMORY_RECORD = "memory_record"
    EVALUATION = "evaluation"
    LEARNING_PROPOSAL = "learning_proposal"
    VALIDATION_RESULT = "validation_result"
    MODEL_UPDATE = "model_update"
    CYCLE_STATUS = "cycle_status"
    FAILURE = "failure"


class EpistemicStatus(StrEnum):
    OBSERVED = "observed"
    INTERPRETED = "interpreted"
    INFERRED = "inferred"
    ASSUMED = "assumed"
    HYPOTHETICAL = "hypothetical"
    BELIEVED = "believed"
    UNCERTAIN = "uncertain"
    UNKNOWN = "unknown"
    CONTRADICTED = "contradicted"


# These are deliberately strict.  A schema that permits absent causal fields
# would recreate the precise information-loss problem this foundation exists
# to prevent.  The Artifact envelope supplies identity, timestamps, status,
# producer, provenance and references for every kind.
REQUIRED_DATA_FIELDS: dict[str, frozenset[str]] = {
    ContractKind.OBSERVATION: frozenset(
        {"content", "source", "modality", "observed_at", "reliability"}
    ),
    ContractKind.GOAL: frozenset(
        {"description", "priority", "constraints", "success_criteria"}
    ),
    ContractKind.CYCLE_CONTEXT: frozenset({"observation_ref", "goal_ref"}),
    ContractKind.WORKSPACE_STATE: frozenset(
        {
            "context",
            "active_percept_ids",
            "retrieved_memory_ids",
            "active_goal_ref",
            "self_state",
            "world_state",
            "uncertainties",
        }
    ),
    ContractKind.MEMORY_QUERY: frozenset(
        {
            "query",
            "context",
            "goal_context",
            "memory_types",
            "relevance_threshold",
            "confidence_threshold",
            "limit",
        }
    ),
    ContractKind.MEMORY_RETRIEVAL: frozenset(
        {"query_ref", "memory_ids", "matches", "retrieval_metadata"}
    ),
    ContractKind.COGNITIVE_REQUEST: frozenset(
        {
            "workspace_ref",
            "objective",
            "problem",
            "constraints",
            "available_evidence",
            "required_depth",
        }
    ),
    ContractKind.COGNITIVE_RESULT: frozenset(
        {
            "request_ref",
            "understanding",
            "hypotheses",
            "inferences",
            "candidate_solutions",
            "candidate_plans",
            "predictions",
            "simulations",
            "uncertainty",
            "assumptions",
            "provenance",
        }
    ),
    ContractKind.DECISION_REQUEST: frozenset(
        {
            "workspace_ref",
            "active_goal_ref",
            "cognitive_result_refs",
            "constraints",
            "values",
            "risks",
            "permissions",
        }
    ),
    ContractKind.DECISION: frozenset(
        {
            "request_ref",
            "goal_ref",
            "selected_option",
            "selected_plan",
            "rationale",
            "expected_outcome",
            "risk",
            "reversibility",
        }
    ),
    ContractKind.ACTION_INTENT: frozenset(
        {
            "decision_ref",
            "goal_ref",
            "action",
            "target",
            "parameters",
            "expected_outcome",
            "constraints",
            "risk_level",
            "authorization",
            "success_criteria",
            "expiration",
        }
    ),
    ContractKind.ACTION_EXECUTION: frozenset({"intent_ref", "idempotency_key"}),
    ContractKind.ACTION_RESULT: frozenset(
        {
            "intent_ref",
            "execution_ref",
            "status",
            "actual_action",
            "observed_result",
            "errors",
            "side_effects",
            "executed_at",
            "evidence",
        }
    ),
    ContractKind.EXPERIENCE: frozenset(
        {
            "context",
            "observation_refs",
            "action_intent_ref",
            "action_result_ref",
            "expected_outcome",
            "actual_outcome",
            "prediction_error",
            "consequences",
            "occurred_at",
        }
    ),
    ContractKind.MEMORY_RECORD: frozenset(
        {
            "memory_key",
            "memory_type",
            "content",
            "evidence_refs",
            "confidence",
            "importance",
            "record_version",
            "supersedes",
            "consolidation_state",
        }
    ),
    ContractKind.EVALUATION: frozenset(
        {
            "experience_ref",
            "expected_outcome",
            "actual_outcome",
            "outcome_status",
            "success",
            "prediction_error",
            "lessons",
        }
    ),
    ContractKind.LEARNING_PROPOSAL: frozenset(
        {
            "source_experience_refs",
            "evaluation_ref",
            "proposed_change",
            "target_system",
            "evidence_refs",
            "expected_benefit",
            "risks",
            "validation_status",
        }
    ),
    ContractKind.VALIDATION_RESULT: frozenset(
        {
            "proposal_ref",
            "status",
            "reason",
            "base_version",
            "target_system",
        }
    ),
    ContractKind.MODEL_UPDATE: frozenset(
        {
            "target",
            "previous_version",
            "new_version",
            "change",
            "evidence_refs",
            "reason",
            "created_by",
        }
    ),
    ContractKind.CYCLE_STATUS: frozenset({"status", "checkpoint"}),
    ContractKind.FAILURE: frozenset({"stage", "error_type", "message"}),
}


def now_utc() -> str:
    """Return an unambiguous, JSON-safe UTC timestamp."""

    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    """Create a non-reusable artifact identifier with a readable type prefix."""

    return f"{prefix}_{uuid4().hex}"


def _ensure_json(value: Any, *, field: str) -> None:
    try:
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError) as error:
        raise ContractError(f"{field} must be JSON serializable: {error}") from error


def canonical_json(value: Any) -> str:
    """Stable JSON used for storage and integrity hashing."""

    _ensure_json(value, field="value")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class Artifact:
    """Immutable envelope shared by all Virtual Brain contracts.

    ``input_refs`` form the causal graph; ``source_refs`` retain external or
    internal provenance; ``epistemic_status`` prevents inferred information
    from silently becoming an observed fact.
    """

    id: str
    kind: str
    cycle_id: str
    producer: str
    data: Mapping[str, Any]
    input_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    epistemic_status: str = EpistemicStatus.OBSERVED
    confidence: float | None = None
    status: str = "active"
    schema_version: str = SCHEMA_VERSION
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.id or not self.cycle_id or not self.producer:
            raise ContractError("artifact id, cycle_id and producer are required")
        if self.kind not in REQUIRED_DATA_FIELDS:
            raise ContractError(f"unknown contract kind: {self.kind}")
        if self.epistemic_status not in {item.value for item in EpistemicStatus}:
            raise ContractError(f"invalid epistemic status: {self.epistemic_status}")
        missing = REQUIRED_DATA_FIELDS[self.kind].difference(self.data.keys())
        if missing:
            raise ContractError(
                f"{self.kind} is missing required data fields: {', '.join(sorted(missing))}"
            )
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ContractError("confidence must be between 0 and 1")
        if not self.created_at:
            object.__setattr__(self, "created_at", now_utc())
        _ensure_json(self.to_dict(), field=f"artifact {self.id}")

    @classmethod
    def create(
        cls,
        kind: ContractKind | str,
        *,
        cycle_id: str,
        producer: str,
        data: Mapping[str, Any],
        input_refs: Sequence[str] = (),
        source_refs: Sequence[str] = (),
        epistemic_status: EpistemicStatus | str = EpistemicStatus.OBSERVED,
        confidence: float | None = None,
        status: str = "active",
        artifact_id: str | None = None,
    ) -> "Artifact":
        kind_value = str(kind)
        return cls(
            id=artifact_id or new_id(kind_value),
            kind=kind_value,
            cycle_id=cycle_id,
            producer=producer,
            data=dict(data),
            input_refs=tuple(input_refs),
            source_refs=tuple(source_refs),
            epistemic_status=str(epistemic_status),
            confidence=confidence,
            status=status,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "cycle_id": self.cycle_id,
            "producer": self.producer,
            "data": dict(self.data),
            "input_refs": list(self.input_refs),
            "source_refs": list(self.source_refs),
            "epistemic_status": self.epistemic_status,
            "confidence": self.confidence,
            "status": self.status,
            "schema_version": self.schema_version,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Artifact":
        return cls(
            id=str(raw["id"]),
            kind=str(raw["kind"]),
            cycle_id=str(raw["cycle_id"]),
            producer=str(raw["producer"]),
            data=dict(raw["data"]),
            input_refs=tuple(raw.get("input_refs", ())),
            source_refs=tuple(raw.get("source_refs", ())),
            epistemic_status=str(raw.get("epistemic_status", EpistemicStatus.OBSERVED)),
            confidence=raw.get("confidence"),
            status=str(raw.get("status", "active")),
            schema_version=str(raw.get("schema_version", SCHEMA_VERSION)),
            created_at=str(raw.get("created_at", "")),
        )
