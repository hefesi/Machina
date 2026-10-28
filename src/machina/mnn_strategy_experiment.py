"""Append-only audit log for human-controlled strategy experiments.

The log records proposals and observed outcomes. It never executes actions or
changes the agent's policy; adopting a candidate remains an explicit caller decision.
"""
from __future__ import annotations

import hashlib
import math
from typing import Mapping

from .fragment_memory import FragmentMemory, MemoryFragment


class MNNStrategyExperimentLog:
    """Persist review and outcome events as immutable memory fragments."""

    def __init__(self, memory: FragmentMemory, actions: tuple[str, ...] | list[str]) -> None:
        if not isinstance(memory, FragmentMemory):
            raise ValueError("memory must be a FragmentMemory")
        names = tuple(actions)
        if len(names) < 2 or any(not isinstance(a, str) or not a.strip() for a in names):
            raise ValueError("at least two non-empty action names are required")
        if len(set(names)) != len(names):
            raise ValueError("action names must be unique")
        self.memory = memory
        self.actions = names

    @staticmethod
    def _required_text(value: str, name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
        return value.strip()

    def _persist(self, experiment_id: str, event: str, content: str,
                 metadata: dict) -> MemoryFragment:
        key = hashlib.sha256(f"{experiment_id}:{event}".encode("utf-8")).hexdigest()
        fragment_id = f"strategy_experiment_{key}"
        expected = {**metadata, "experiment_id": experiment_id, "event": event}
        try:
            existing = self.memory.get(fragment_id, record_access=False)
        except KeyError:
            return self.memory.add(
                content,
                kind="strategy-experiment",
                source_uri=f"machina://strategy-experiment/{key}",
                importance=0.8,
                confidence=1.0,
                tags=("strategy-experiment", event),
                metadata=expected,
                pinned=True,
                fragment_id=fragment_id,
            )
        if existing.content != content or dict(existing.metadata) != expected:
            raise ValueError("experiment event ID already exists with different data")
        return existing

    def begin(
        self, experiment_id: str, *, hypothesis: str, context: str,
        current_action: str, planned_action: str, review: Mapping,
    ) -> MemoryFragment:
        """Record a proposed controlled trial; no action is executed here."""
        experiment_id = self._required_text(experiment_id, "experiment_id")
        hypothesis = self._required_text(hypothesis, "hypothesis")
        context = self._required_text(context, "context")
        if current_action not in self.actions:
            raise ValueError("current_action must be a configured action")
        if planned_action not in self.actions:
            raise ValueError("planned_action must be a configured action")
        if not isinstance(review, Mapping):
            raise ValueError("review must be a mapping returned by the strategy reviewer")
        status = review.get("status")
        if not isinstance(status, str) or status not in {"candidate", "maintain", "abstain"}:
            raise ValueError("review status must be candidate, maintain, or abstain")
        candidate = review.get("candidate_action")
        if candidate is not None and candidate not in self.actions:
            raise ValueError("review candidate_action is not configured")
        if status == "candidate" and candidate is None:
            raise ValueError("candidate review must include candidate_action")
        content = f"Strategy experiment proposal '{experiment_id}': {hypothesis}"
        return self._persist(experiment_id, "proposal", content, {
            "hypothesis": hypothesis,
            "context": context,
            "current_action": current_action,
            "planned_action": planned_action,
            "candidate_action": candidate,
            "review_status": status,
            "review_reason": review.get("reason"),
            "evidence_ids": self._evidence_ids(review),
            "execution": "not_executed_by_log",
        })

    def complete(
        self, experiment_id: str, *, tested_action: str, observed_reward: float,
        decision: str, observation: str = "",
    ) -> MemoryFragment:
        """Append an observed result and a review decision, without applying it."""
        experiment_id = self._required_text(experiment_id, "experiment_id")
        if tested_action not in self.actions:
            raise ValueError("tested_action must be a configured action")
        if isinstance(observed_reward, bool) or not isinstance(observed_reward, (int, float)) or not math.isfinite(observed_reward):
            raise ValueError("observed_reward must be a finite number")
        allowed = {"keep_current", "validate_candidate_further", "collect_more_data"}
        if not isinstance(decision, str) or decision not in allowed:
            raise ValueError("decision must be keep_current, validate_candidate_further, or collect_more_data")
        if not isinstance(observation, str):
            raise ValueError("observation must be a string")
        proposals = [
            item for item in self.memory.archive()
            if item.kind == "strategy-experiment"
            and item.metadata.get("experiment_id") == experiment_id
            and item.metadata.get("event") == "proposal"
        ]
        if not proposals:
            raise ValueError("cannot complete an experiment without a persisted proposal")
        proposal = proposals[0]
        if proposal.metadata.get("planned_action") != tested_action:
            raise ValueError("tested_action must match the persisted planned_action")
        content = (
            f"Strategy experiment outcome '{experiment_id}': action={tested_action}, "
            f"reward={float(observed_reward):g}, decision={decision}"
        )
        return self._persist(experiment_id, "outcome", content, {
            "tested_action": tested_action,
            "observed_reward": float(observed_reward),
            "decision": decision,
            "observation": observation.strip(),
            "proposal_fragment_id": proposal.id,
            "policy_changed": False,
        })

    @staticmethod
    def _evidence_ids(review: Mapping) -> list[str]:
        result = []
        evidence = review.get("evidence", {})
        if isinstance(evidence, Mapping):
            for item in evidence.values():
                if isinstance(item, Mapping):
                    for key in ("previous_evidence_ids", "recent_evidence_ids"):
                        values = item.get(key, [])
                        if isinstance(values, list):
                            result.extend(value for value in values if isinstance(value, str))
        drift = review.get("drift_report", {})
        if isinstance(drift, Mapping):
            comparisons = drift.get("comparisons", {})
            if isinstance(comparisons, Mapping):
                for item in comparisons.values():
                    if isinstance(item, Mapping):
                        for key in ("previous_evidence_ids", "recent_evidence_ids"):
                            values = item.get(key, [])
                            if isinstance(values, list):
                                result.extend(value for value in values if isinstance(value, str))
        return list(dict.fromkeys(result))
