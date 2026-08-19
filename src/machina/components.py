"""Replaceable cognitive-loop components.

Components only return data.  They do not receive a database handle and thus
cannot bypass the ownership rule by silently writing another component's
persistent state.  The orchestrator records their outputs as contracts.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import re
from typing import Any, Protocol

from .contracts import Artifact, now_utc


class CognitionEngine(Protocol):
    def analyze(
        self,
        *,
        observation: Artifact,
        workspace: Artifact,
        retrieval: Artifact,
        goal: Artifact,
        request: Artifact,
    ) -> Mapping[str, Any]: ...


class AgencyPolicy(Protocol):
    def decide(
        self,
        *,
        goal: Artifact,
        workspace: Artifact,
        cognitive_result: Artifact,
        request: Artifact,
    ) -> Mapping[str, Any]: ...


class ActionExecutor(Protocol):
    """Execute an intent using ``intent.id`` as the idempotency key.

    A real executor must return the previously observed outcome when called
    again with the same key.  That property makes resumption safe if a process
    stops after dispatching an external action but before recording its result.
    """

    def execute(self, intent: Artifact) -> Mapping[str, Any]: ...


class LearningEngine(Protocol):
    def propose(
        self,
        *,
        experience: Artifact,
        evaluation: Artifact,
        goal: Artifact,
        action_intent: Artifact,
    ) -> Mapping[str, Any]: ...


class DeterministicCognition:
    """A safe, inspectable placeholder until an LLM/model is plugged in."""

    def analyze(
        self,
        *,
        observation: Artifact,
        workspace: Artifact,
        retrieval: Artifact,
        goal: Artifact,
        request: Artifact,
    ) -> Mapping[str, Any]:
        content = _text(observation.data["content"])
        source = observation.data["source"]
        target = source.get("name", source.get("id", "environment"))
        recalled = list(retrieval.data["memory_ids"])
        plan = {
            "plan_id": f"plan:{request.id}",
            "action": "acknowledge",
            "target": target,
            "parameters": {"message": content},
            "expected_outcome": "The observation is acknowledged and recorded.",
            "evidence_refs": [observation.id, *recalled],
        }
        return {
            "request_ref": request.id,
            "understanding": {
                "summary": content,
                "goal": goal.data["description"],
                "recalled_memory_count": len(recalled),
            },
            "hypotheses": [],
            "inferences": [],
            "candidate_solutions": [plan],
            "candidate_plans": [plan],
            "predictions": [
                {
                    "action": plan["action"],
                    "expected_outcome": plan["expected_outcome"],
                    "status": "hypothetical",
                }
            ],
            "simulations": [],
            "uncertainty": [],
            "assumptions": [
                "The default cognition engine only acknowledges an observation."
            ],
            "provenance": [observation.id, *recalled],
        }


class FirstCandidateAgency:
    """Select the first candidate while preserving the full rationale trail."""

    def decide(
        self,
        *,
        goal: Artifact,
        workspace: Artifact,
        cognitive_result: Artifact,
        request: Artifact,
    ) -> Mapping[str, Any]:
        plans = cognitive_result.data["candidate_plans"]
        if not plans:
            raise ValueError("Agency cannot decide without a candidate plan")
        plan = dict(plans[0])
        return {
            "request_ref": request.id,
            "goal_ref": goal.id,
            "selected_option": plan,
            "selected_plan": plan,
            "rationale": {
                "policy": "first_candidate",
                "cognitive_result_ref": cognitive_result.id,
                "evidence_refs": list(cognitive_result.input_refs),
            },
            "expected_outcome": plan["expected_outcome"],
            "risk": "low",
            "reversibility": "reversible",
        }


class AcknowledgeExecutor:
    """Default executor with no external side effects."""

    def execute(self, intent: Artifact) -> Mapping[str, Any]:
        return {
            "status": "succeeded",
            "actual_action": {
                "action": intent.data["action"],
                "target": intent.data["target"],
                "parameters": intent.data["parameters"],
            },
            "observed_result": {
                "acknowledged": True,
                "message": intent.data["parameters"].get("message"),
            },
            "errors": [],
            "side_effects": [],
            "executed_at": now_utc(),
            "evidence": [{"executor": "acknowledge", "intent_id": intent.id}],
        }


class OutcomeLearner:
    """Turns an evaluated outcome into a proposal, never a direct write."""

    def propose(
        self,
        *,
        experience: Artifact,
        evaluation: Artifact,
        goal: Artifact,
        action_intent: Artifact,
    ) -> Mapping[str, Any]:
        succeeded = bool(evaluation.data["success"])
        outcome = evaluation.data["actual_outcome"]
        action = action_intent.data["action"]
        lesson = {
            "statement": (
                f"For goal '{goal.data['description']}', action '{action}' "
                f"completed with status '{evaluation.data['outcome_status']}'."
            ),
            "outcome": outcome,
            "epistemic_status": "observed" if succeeded else "uncertain",
        }
        return {
            "source_experience_refs": [experience.id],
            "evaluation_ref": evaluation.id,
            "proposed_change": lesson,
            "target_system": "memory",
            "evidence_refs": [experience.id, evaluation.id, action_intent.id],
            "expected_benefit": "Make a verified action outcome available to future cycles.",
            "risks": [] if succeeded else ["The action did not succeed; do not generalize it."],
            "validation_status": "pending",
        }


class MemoryRepository:
    """Read-only retrieval projection over the append-only journal."""

    def __init__(self, store: Any) -> None:
        self._store = store

    def retrieve(self, query: Artifact) -> Mapping[str, Any]:
        candidates = self._store.artifacts_for_event_types(
            ("memory.episode_recorded", "memory.consolidated")
        )
        query_terms = _terms(
            " ".join(
                [
                    _text(query.data["query"]),
                    _text(query.data["goal_context"]),
                    _text(query.data["context"]),
                ]
            )
        )
        matches: list[dict[str, Any]] = []
        for memory in candidates:
            if memory.data["memory_type"] not in query.data["memory_types"]:
                continue
            if float(memory.data["confidence"]) < float(query.data["confidence_threshold"]):
                continue
            memory_terms = _terms(_text(memory.data["content"]))
            relevance = _overlap(query_terms, memory_terms)
            if relevance < float(query.data["relevance_threshold"]):
                continue
            matches.append(
                {
                    "memory_id": memory.id,
                    "relevance": relevance,
                    "confidence": memory.data["confidence"],
                    "memory_type": memory.data["memory_type"],
                    "provenance": list(memory.source_refs),
                }
            )
        matches.sort(key=lambda item: (item["relevance"], item["confidence"]), reverse=True)
        matches = matches[: int(query.data["limit"])]
        return {
            "query_ref": query.id,
            "memory_ids": [match["memory_id"] for match in matches],
            "matches": matches,
            "retrieval_metadata": {
                "candidate_count": len(candidates),
                "returned_count": len(matches),
                "method": "token_overlap_v1",
            },
        }

    def latest_version(self, memory_key: str) -> tuple[int, str | None]:
        records = self._store.artifacts_for_event_types(("memory.consolidated",))
        matching = [
            record for record in records if record.data.get("memory_key") == memory_key
        ]
        if not matching:
            return 0, None
        latest = max(matching, key=lambda item: int(item.data["record_version"]))
        return int(latest.data["record_version"]), latest.id


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _terms(value: str) -> set[str]:
    return set(re.findall(r"[\wÀ-ÿ]+", value.lower()))


def _overlap(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left.intersection(right)) / len(left.union(right))
