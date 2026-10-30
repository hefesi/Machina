"""Bridge MNN strategy decisions into VirtualBrain's append-only EventStore.

The EventStore remains the authoritative causal journal. This bridge does not
write to FragmentMemory, avoiding an unsafe dual-write across independent DBs.
Stable IDs support sequential retries; concurrent callers should be serialized.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import Artifact, ContractKind, EpistemicStatus
from .event_store import EventStore, StoredEvent


class MNNStrategyEventBridge:
    """Persist strategy proposals and confirmed outcomes in a brain event chain."""

    def __init__(self, store: EventStore) -> None:
        if not isinstance(store, EventStore):
            raise ValueError("store must be an EventStore")
        self.store = store

    @staticmethod
    def _identifier(name: str, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _score(name: str, value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be within [0, 1]")
        return float(value)

    @staticmethod
    def _evidence_ids(value: object) -> list[str]:
        if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
            raise ValueError("evidence_ids must be a sequence of unique non-empty strings")
        result: list[str] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("evidence_ids must contain only non-empty strings")
            item = item.strip()
            if item in seen:
                raise ValueError("evidence_ids must not contain duplicates")
            seen.add(item)
            result.append(item)
        return result

    def record_proposal(
        self,
        cycle_id: str,
        proposal: Mapping[str, Any],
        *,
        expected_reward: float,
        proposal_id: str,
    ) -> StoredEvent:
        """Append a proposal or abstention; this never represents execution."""
        self._identifier("cycle_id", cycle_id)
        if not self.store.has_cycle(cycle_id):
            raise KeyError(f"unknown cycle: {cycle_id}")
        if not isinstance(proposal, Mapping):
            raise ValueError("proposal must be a mapping")
        status = proposal.get("status")
        if not isinstance(status, str) or status not in {"proposed", "abstain"}:
            raise ValueError("proposal status must be 'proposed' or 'abstain'")
        context = proposal.get("context")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("proposal context must be non-empty")
        action = proposal.get("action")
        if status == "proposed":
            if not isinstance(action, str) or not action.strip():
                raise ValueError("actionable proposal must include an action")
            action = action.strip()
        elif action is not None:
            raise ValueError("abstention must not include an action")
        identifier = self._identifier("proposal_id", proposal_id)
        evidence_ids = self._evidence_ids(proposal.get("evidence_ids", ()))
        expected = self._score("expected_reward", expected_reward)
        data = {
            "proposal_id": identifier,
            "status": status,
            "action": action,
            "context": " ".join(context.casefold().split()),
            "expected_reward": expected,
            "evidence_ids": evidence_ids,
            "executed": False,
        }
        artifact_id = f"strategy-proposal:{identifier}"
        for event in self.store.all_events():
            if event.artifact.id == artifact_id:
                if event.cycle_id != cycle_id or event.artifact.data != data:
                    raise ValueError("proposal_id was already used with different data")
                if event.event_type != "strategy.proposal.recorded":
                    raise ValueError("proposal artifact ID is already used by another event")
                return event
        artifact = Artifact.create(
            ContractKind.STRATEGY_PROPOSAL,
            cycle_id=cycle_id,
            producer="mnn_strategy",
            data=data,
            source_refs=evidence_ids,
            epistemic_status=EpistemicStatus.INFERRED,
            artifact_id=artifact_id,
        )
        return self.store.append("strategy.proposal.recorded", artifact)

    def record_outcome(
        self,
        cycle_id: str,
        proposal_id: str,
        *,
        execution_confirmed: bool,
        executed_action: str,
        observed_reward: float,
        operation_id: str,
    ) -> StoredEvent:
        """Append an outcome only for an explicitly confirmed matching action."""
        identifier = self._identifier("proposal_id", proposal_id)
        operation = self._identifier("operation_id", operation_id)
        proposal_event = next(
            (
                event for event in self.store.all_events()
                if event.event_type == "strategy.proposal.recorded"
                and event.artifact.data.get("proposal_id") == identifier
            ),
            None,
        )
        if proposal_event is None:
            raise KeyError(f"unknown strategy proposal: {identifier}")
        if proposal_event.cycle_id != cycle_id:
            raise ValueError("outcome must belong to the proposal's cognitive cycle")
        proposal = proposal_event.artifact.data
        if proposal.get("status") != "proposed":
            raise ValueError("an abstention cannot receive an execution outcome")
        if execution_confirmed is not True:
            raise ValueError("external execution must be explicitly confirmed")
        action = proposal.get("action")
        if not isinstance(executed_action, str) or executed_action != action:
            raise ValueError("executed action does not match the persisted proposal")
        observed = self._score("observed_reward", observed_reward)
        expected = self._score("expected_reward", proposal["expected_reward"])
        error = observed - expected
        data = {
            "proposal_id": identifier,
            "operation_id": operation,
            "action": action,
            "context": proposal["context"],
            "expected_reward": expected,
            "observed_reward": observed,
            "prediction_error": error,
            "execution_confirmed": True,
            "evidence_ids": list(proposal["evidence_ids"]),
        }
        artifact_id = f"strategy-outcome:{operation}"
        for event in self.store.all_events():
            if event.artifact.id == artifact_id:
                if event.cycle_id != cycle_id or event.artifact.data != data:
                    raise ValueError("operation_id was already used with different data")
                if event.event_type != "strategy.outcome.recorded":
                    raise ValueError("outcome artifact ID is already used by another event")
                return event
        artifact = Artifact.create(
            ContractKind.STRATEGY_OUTCOME,
            cycle_id=cycle_id,
            producer="mnn_strategy",
            data=data,
            input_refs=[proposal_event.artifact.id],
            source_refs=list(proposal["evidence_ids"]),
            epistemic_status=EpistemicStatus.OBSERVED,
            artifact_id=artifact_id,
        )
        return self.store.append(
            "strategy.outcome.recorded", artifact,
            causation_id=proposal_event.artifact.id,
        )

    def outcomes_for(self, proposal_id: str) -> list[StoredEvent]:
        identifier = self._identifier("proposal_id", proposal_id)
        return [
            event for event in self.store.all_events()
            if event.event_type == "strategy.outcome.recorded"
            and event.artifact.data.get("proposal_id") == identifier
        ]
