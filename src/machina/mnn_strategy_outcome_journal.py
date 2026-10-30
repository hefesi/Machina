"""Persistent, auditable journal for MNN strategy decisions and outcomes.

This journal stores proposals separately from confirmed executions. Prediction
error is descriptive (observed minus expected reward), not a causal estimate.
"""
from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Mapping
from uuid import uuid4

from .fragment_memory import FragmentMemory, MemoryFragment


class MNNStrategyOutcomeJournal:
    """Persist strategy proposals and separately confirmed outcome records."""

    def __init__(self, memory: FragmentMemory) -> None:
        if not isinstance(memory, FragmentMemory):
            raise ValueError("memory must be a FragmentMemory")
        self.memory = memory

    @staticmethod
    def _score(name: str, value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{name} must be within [0, 1]")
        return float(value)

    @staticmethod
    def _identifier(name: str, value: str | None) -> str:
        if value is None:
            return f"{name}-{uuid4().hex}"
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    @staticmethod
    def _evidence_ids(proposal: Mapping[str, object]) -> list[str]:
        raw = proposal.get("evidence_ids", ())
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            raise ValueError("evidence_ids must be a sequence of non-empty strings")
        evidence_ids: list[str] = []
        seen: set[str] = set()
        for value in raw:
            if not isinstance(value, str) or not value.strip():
                raise ValueError("evidence_ids must contain only non-empty strings")
            identifier = value.strip()
            if identifier in seen:
                raise ValueError("evidence_ids must not contain duplicates")
            seen.add(identifier)
            evidence_ids.append(identifier)
        return evidence_ids

    def record_proposal(
        self,
        proposal: Mapping[str, object],
        *,
        expected_reward: float,
        proposal_id: str | None = None,
    ) -> MemoryFragment:
        """Persist an advisory proposal (including abstention) without execution."""
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
        evidence_ids = self._evidence_ids(proposal)
        expected = self._score("expected_reward", expected_reward)
        identifier = self._identifier("proposal", proposal_id)
        fragment_id = f"mnn-strategy-proposal-{identifier}"
        metadata = {
            "record_type": "proposal",
            "proposal_id": identifier,
            "status": status,
            "action": action,
            "context": " ".join(context.casefold().split()),
            "expected_reward": expected,
            "evidence_ids": evidence_ids,
            "executed": False,
        }
        try:
            existing = self.memory.get(fragment_id, record_access=False)
        except KeyError:
            return self.memory.add(
                content=f"Strategy proposal {identifier}: {status} in {metadata['context']}",
                kind="mnn-strategy-journal",
                source_uri=f"machina://strategy/proposal/{identifier}",
                importance=0.5,
                confidence=1.0,
                tags=("mnn", "strategy", "proposal"),
                metadata=metadata,
                fragment_id=fragment_id,
            )
        if dict(existing.metadata) != metadata:
            raise ValueError("proposal_id was already used with different proposal data")
        return existing

    def record_outcome(
        self,
        proposal_id: str,
        *,
        execution_confirmed: bool,
        executed_action: str,
        observed_reward: float,
        operation_id: str | None = None,
    ) -> MemoryFragment:
        """Persist only a matching confirmed action and its prediction error."""
        identifier = self._identifier("proposal_id", proposal_id)
        proposal_fragment = self.memory.get(
            f"mnn-strategy-proposal-{identifier}", record_access=False
        )
        proposal = dict(proposal_fragment.metadata)
        if proposal.get("record_type") != "proposal" or proposal.get("status") != "proposed":
            raise ValueError("only an actionable proposal can receive an outcome")
        if execution_confirmed is not True:
            raise ValueError("external execution must be explicitly confirmed")
        action = proposal.get("action")
        if not isinstance(executed_action, str) or executed_action != action:
            raise ValueError("executed action does not match the persisted proposal")
        observed = self._score("observed_reward", observed_reward)
        expected = self._score("expected_reward", proposal.get("expected_reward"))
        operation = self._identifier("outcome", operation_id)
        fragment_id = f"mnn-strategy-outcome-{operation}"
        metadata = {
            "record_type": "outcome",
            "operation_id": operation,
            "proposal_id": identifier,
            "action": action,
            "context": proposal["context"],
            "expected_reward": expected,
            "observed_reward": observed,
            "prediction_error": observed - expected,
            "execution_confirmed": True,
            "evidence_ids": list(proposal.get("evidence_ids", ())),
        }
        try:
            existing = self.memory.get(fragment_id, record_access=False)
        except KeyError:
            return self.memory.add(
                content=(
                    f"Strategy outcome {operation}: expected {expected:.6f}, "
                    f"observed {observed:.6f}, prediction error {observed - expected:.6f}"
                ),
                kind="mnn-strategy-journal",
                source_uri=f"machina://strategy/outcome/{operation}",
                importance=min(1.0, abs(observed - expected)),
                confidence=1.0,
                tags=("mnn", "strategy", "outcome", "confirmed-execution"),
                related_ids=(proposal_fragment.id,),
                metadata=metadata,
                fragment_id=fragment_id,
            )
        if dict(existing.metadata) != metadata:
            raise ValueError("operation_id was already used with different outcome data")
        return existing

    def outcomes_for(self, proposal_id: str) -> list[MemoryFragment]:
        """Return persisted outcomes for one proposal, oldest first."""
        identifier = self._identifier("proposal_id", proposal_id)
        return [
            item for item in self.memory.archive()
            if item.kind == "mnn-strategy-journal"
            and item.metadata.get("record_type") == "outcome"
            and item.metadata.get("proposal_id") == identifier
        ]
