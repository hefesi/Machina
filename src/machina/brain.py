"""The durable, resumable Virtual Brain v0.1 orchestration loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .components import (
    AcknowledgeExecutor,
    ActionExecutor,
    AgencyPolicy,
    CognitionEngine,
    DeterministicCognition,
    FirstCandidateAgency,
    LearningEngine,
    MemoryRepository,
    OutcomeLearner,
)
from .contracts import Artifact, ContractKind, EpistemicStatus, new_id, now_utc
from .event_store import CycleNotFoundError, EventStore, StoredEvent


@dataclass(frozen=True, slots=True)
class CycleResult:
    cycle_id: str
    status: str
    events: tuple[StoredEvent, ...]
    observation_id: str
    goal_id: str
    experience_id: str | None
    model_update_id: str | None


@dataclass(frozen=True, slots=True)
class CycleAudit:
    """Evidence that one persisted cycle satisfies the v0.1 invariants."""

    cycle_id: str
    valid: bool
    errors: tuple[str, ...]
    event_count: int

    def assert_valid(self) -> None:
        if not self.valid:
            raise AssertionError("; ".join(self.errors))


class VirtualBrain:
    """Implementation of the documented Virtual Brain cognitive cycle.

    The concrete defaults are deliberately modest.  The value of this first
    core is the durable boundary between components, not pretending that its
    deterministic cognition is an AGI.  Plug-ins can replace cognition,
    agency, learning and execution while the journal and contracts stay fixed.
    """

    def __init__(
        self,
        storage_path: str | Path,
        *,
        cognition: CognitionEngine | None = None,
        agency: AgencyPolicy | None = None,
        action_executor: ActionExecutor | None = None,
        learning: LearningEngine | None = None,
    ) -> None:
        self.store = EventStore(storage_path)
        self.cognition = cognition or DeterministicCognition()
        self.agency = agency or FirstCandidateAgency()
        self.action_executor = action_executor or AcknowledgeExecutor()
        self.learning = learning or OutcomeLearner()
        self.memory = MemoryRepository(self.store)

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "VirtualBrain":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def start_cycle(
        self,
        observation: Any,
        objective: str | Mapping[str, Any],
        *,
        source: Mapping[str, Any] | None = None,
        modality: str = "event",
        constraints: Sequence[str] = (),
        success_criteria: Sequence[str] = (),
        priority: int = 0,
    ) -> str:
        """Durably record an observation and goal before any reasoning occurs."""

        cycle_id = new_id("cycle")
        self.store.create_cycle(cycle_id)
        source_data = dict(source or {})
        source_data.setdefault("id", new_id("source"))
        source_data.setdefault("type", "user")
        source_data.setdefault("name", "user")
        source_data.setdefault("reliability", 1.0)
        observation_artifact = Artifact.create(
            ContractKind.OBSERVATION,
            cycle_id=cycle_id,
            producer="perception",
            data={
                "content": observation,
                "source": source_data,
                "modality": modality,
                "observed_at": now_utc(),
                "reliability": source_data["reliability"],
                "raw_reference": None,
            },
            source_refs=[str(source_data["id"])],
            epistemic_status=EpistemicStatus.OBSERVED,
            confidence=1.0,
        )
        goal_data = self._goal_data(
            objective,
            constraints=constraints,
            success_criteria=success_criteria,
            priority=priority,
        )
        goal_artifact = Artifact.create(
            ContractKind.GOAL,
            cycle_id=cycle_id,
            producer="agency",
            data=goal_data,
            input_refs=[observation_artifact.id],
            source_refs=[str(source_data["id"])],
            epistemic_status=EpistemicStatus.INTERPRETED,
            confidence=1.0,
        )
        context = Artifact.create(
            ContractKind.CYCLE_CONTEXT,
            cycle_id=cycle_id,
            producer="orchestrator",
            data={
                "observation_ref": observation_artifact.id,
                "goal_ref": goal_artifact.id,
            },
            input_refs=[observation_artifact.id, goal_artifact.id],
            source_refs=[str(source_data["id"])],
            epistemic_status=EpistemicStatus.OBSERVED,
        )
        self.store.append("observation.received", observation_artifact)
        self.store.append("goal.activated", goal_artifact, causation_id=observation_artifact.id)
        self.store.append("cycle.started", context, causation_id=goal_artifact.id)
        return cycle_id

    def run_cycle(
        self,
        observation: Any,
        objective: str | Mapping[str, Any],
        **kwargs: Any,
    ) -> CycleResult:
        cycle_id = self.start_cycle(observation, objective, **kwargs)
        result = self.advance(cycle_id)
        if result is None:  # defensive: no stop checkpoint was requested
            raise RuntimeError("cycle did not reach a terminal state")
        return result

    def pause(self, cycle_id: str, *, checkpoint: str, reason: str = "requested") -> None:
        self._require_cycle(cycle_id)
        status = Artifact.create(
            ContractKind.CYCLE_STATUS,
            cycle_id=cycle_id,
            producer="orchestrator",
            data={"status": "paused", "checkpoint": checkpoint, "reason": reason},
            epistemic_status=EpistemicStatus.OBSERVED,
        )
        self.store.append("cycle.paused", status)

    def resume(
        self, cycle_id: str, *, stop_after: str | None = None
    ) -> CycleResult | None:
        """Resume from durable artifacts; never repeat already-recorded stages."""

        self._require_cycle(cycle_id)
        if self.store.latest_artifact(cycle_id, "cycle.completed"):
            return self._result(cycle_id)
        resumed = Artifact.create(
            ContractKind.CYCLE_STATUS,
            cycle_id=cycle_id,
            producer="orchestrator",
            data={"status": "resumed", "checkpoint": "resume"},
            epistemic_status=EpistemicStatus.OBSERVED,
        )
        self.store.append("cycle.resumed", resumed)
        return self.advance(cycle_id, stop_after=stop_after)

    def audit_cycle(self, cycle_id: str) -> CycleAudit:
        """Check the persisted causal graph against the documented v0.1 loop.

        This is deliberately a verification operation, not a best-effort log
        viewer.  A completed cycle only passes if each mandatory hand-off is
        present, every internal reference resolves, and validation/consolidation
        obey the proposal → validate → commit boundary.
        """

        self._require_cycle(cycle_id)
        errors: list[str] = []
        try:
            self.store.verify_integrity()
        except Exception as error:
            errors.append(f"journal integrity failed: {error}")

        events = self.store.events_for_cycle(cycle_id)
        all_artifacts = {
            event.artifact.id: event.artifact for event in self.store.all_events()
        }
        for event in events:
            for reference in event.artifact.input_refs:
                if reference not in all_artifacts:
                    errors.append(
                        f"{event.event_type} ({event.artifact.id}) has unresolved input {reference}"
                    )

        by_type = {event.event_type: event.artifact for event in events}
        ordered_core = [
            "observation.received",
            "goal.activated",
            "cycle.started",
            "workspace.updated",
            "memory.retrieval_requested",
            "memory.retrieved",
            "cognition.requested",
            "cognition.completed",
            "workspace.cognition_updated",
            "decision.requested",
            "decision.made",
            "action.intent_created",
            "action.execution_started",
            "action.result",
            "experience.created",
            "memory.episode_recorded",
            "evaluation.completed",
            "learning.proposed",
            "consolidation.validated",
        ]
        completed = "cycle.completed" in by_type
        if completed:
            missing = [name for name in ordered_core if name not in by_type]
            if missing:
                errors.append(f"completed cycle misses required stages: {', '.join(missing)}")
            else:
                observed_order = [
                    event.event_type
                    for event in events
                    if event.event_type in ordered_core
                ]
                if observed_order != ordered_core:
                    errors.append("required stages are not in cognitive-loop order")

        observation = by_type.get("observation.received")
        cognitive = by_type.get("cognition.completed")
        action_result = by_type.get("action.result")
        experience = by_type.get("experience.created")
        proposal = by_type.get("learning.proposed")
        validation = by_type.get("consolidation.validated")
        if observation and observation.epistemic_status != EpistemicStatus.OBSERVED:
            errors.append("observation must remain epistemically observed")
        if cognitive and cognitive.epistemic_status != EpistemicStatus.INFERRED:
            errors.append("cognitive result must remain epistemically inferred")
        if experience and action_result:
            if experience.data["action_result_ref"] != action_result.id:
                errors.append("experience does not preserve its action result reference")
        if proposal and experience:
            if experience.id not in proposal.data["source_experience_refs"]:
                errors.append("learning proposal does not preserve source experience")

        if validation:
            approved = validation.data["status"] == "approved"
            has_memory = "memory.consolidated" in by_type
            has_update = "model.updated" in by_type
            if approved and not (has_memory and has_update):
                errors.append("approved proposal lacks versioned memory/model update")
            if not approved and (has_memory or has_update):
                errors.append("rejected proposal changed persistent semantic memory")
            if has_update and proposal:
                update = by_type["model.updated"]
                if proposal.id not in update.input_refs:
                    errors.append("model update is not causally linked to learning proposal")

        return CycleAudit(
            cycle_id=cycle_id,
            valid=not errors,
            errors=tuple(errors),
            event_count=len(events),
        )

    def advance(
        self, cycle_id: str, *, stop_after: str | None = None
    ) -> CycleResult | None:
        """Drive a started cycle until completion or an explicitly durable pause.

        ``stop_after`` is intentionally public.  It makes each boundary easy
        to test and provides a controlled interruption mechanism for a longer
        running executor.
        """

        self._require_cycle(cycle_id)
        if self.store.latest_artifact(cycle_id, "cycle.completed"):
            return self._result(cycle_id)
        try:
            observation = self._required(cycle_id, "observation.received")
            goal = self._required(cycle_id, "goal.activated")

            workspace = self._stage(
                cycle_id,
                "workspace.updated",
                lambda: self._initial_workspace(observation, goal),
            )
            if self._stop_if_requested(cycle_id, "workspace.updated", stop_after):
                return None

            memory_query = self._stage(
                cycle_id,
                "memory.retrieval_requested",
                lambda: self._memory_query(observation, workspace, goal),
            )
            if self._stop_if_requested(cycle_id, "memory.retrieval_requested", stop_after):
                return None

            retrieval = self._stage(
                cycle_id,
                "memory.retrieved",
                lambda: self._memory_retrieval(memory_query),
            )
            if self._stop_if_requested(cycle_id, "memory.retrieved", stop_after):
                return None

            cognitive_request = self._stage(
                cycle_id,
                "cognition.requested",
                lambda: self._cognitive_request(observation, workspace, retrieval, goal),
            )
            if self._stop_if_requested(cycle_id, "cognition.requested", stop_after):
                return None

            cognitive_result = self._stage(
                cycle_id,
                "cognition.completed",
                lambda: self._cognitive_result(
                    observation, workspace, retrieval, goal, cognitive_request
                ),
            )
            if self._stop_if_requested(cycle_id, "cognition.completed", stop_after):
                return None

            enriched_workspace = self._stage(
                cycle_id,
                "workspace.cognition_updated",
                lambda: self._enriched_workspace(workspace, cognitive_result),
            )
            if self._stop_if_requested(cycle_id, "workspace.cognition_updated", stop_after):
                return None

            decision_request = self._stage(
                cycle_id,
                "decision.requested",
                lambda: self._decision_request(goal, enriched_workspace, cognitive_result),
            )
            if self._stop_if_requested(cycle_id, "decision.requested", stop_after):
                return None

            decision = self._stage(
                cycle_id,
                "decision.made",
                lambda: self._decision(goal, enriched_workspace, cognitive_result, decision_request),
            )
            if self._stop_if_requested(cycle_id, "decision.made", stop_after):
                return None

            intent = self._stage(
                cycle_id,
                "action.intent_created",
                lambda: self._action_intent(goal, decision),
            )
            if self._stop_if_requested(cycle_id, "action.intent_created", stop_after):
                return None

            execution = self._stage(
                cycle_id,
                "action.execution_started",
                lambda: self._action_execution(intent),
            )
            if self._stop_if_requested(cycle_id, "action.execution_started", stop_after):
                return None

            action_result = self._stage(
                cycle_id,
                "action.result",
                lambda: self._action_result(intent, execution),
            )
            if self._stop_if_requested(cycle_id, "action.result", stop_after):
                return None

            experience = self._stage(
                cycle_id,
                "experience.created",
                lambda: self._experience(observation, enriched_workspace, intent, action_result),
            )
            if self._stop_if_requested(cycle_id, "experience.created", stop_after):
                return None

            episode = self._stage(
                cycle_id,
                "memory.episode_recorded",
                lambda: self._episode_memory(experience, observation, intent, action_result),
            )
            if self._stop_if_requested(cycle_id, "memory.episode_recorded", stop_after):
                return None

            evaluation = self._stage(
                cycle_id,
                "evaluation.completed",
                lambda: self._evaluation(experience, action_result),
            )
            if self._stop_if_requested(cycle_id, "evaluation.completed", stop_after):
                return None

            proposal = self._stage(
                cycle_id,
                "learning.proposed",
                lambda: self._learning_proposal(experience, evaluation, goal, intent),
            )
            if self._stop_if_requested(cycle_id, "learning.proposed", stop_after):
                return None

            validation = self._stage(
                cycle_id,
                "consolidation.validated",
                lambda: self._validation(proposal, evaluation),
            )
            if self._stop_if_requested(cycle_id, "consolidation.validated", stop_after):
                return None

            if validation.data["status"] == "approved":
                memory = self._stage(
                    cycle_id,
                    "memory.consolidated",
                    lambda: self._consolidated_memory(proposal, validation),
                )
                if self._stop_if_requested(cycle_id, "memory.consolidated", stop_after):
                    return None
                self._stage(
                    cycle_id,
                    "model.updated",
                    lambda: self._model_update(proposal, validation, memory),
                )
                if self._stop_if_requested(cycle_id, "model.updated", stop_after):
                    return None

            self._stage(
                cycle_id,
                "cycle.completed",
                lambda: self._completed_status(cycle_id, experience, episode, proposal, validation),
            )
            return self._result(cycle_id)
        except Exception as error:
            self._record_failure(cycle_id, error)
            raise

    def _stage(self, cycle_id: str, event_type: str, factory: Any) -> Artifact:
        existing = self.store.latest_artifact(cycle_id, event_type)
        if existing is not None:
            return existing
        artifact = factory()
        self.store.append(event_type, artifact, causation_id=artifact.input_refs[-1] if artifact.input_refs else None)
        return artifact

    def _initial_workspace(self, observation: Artifact, goal: Artifact) -> Artifact:
        source = observation.data["source"]
        return Artifact.create(
            ContractKind.WORKSPACE_STATE,
            cycle_id=observation.cycle_id,
            producer="workspace",
            data={
                "context": {"latest_observation": observation.data["content"]},
                "active_percept_ids": [observation.id],
                "retrieved_memory_ids": [],
                "active_goal_ref": goal.id,
                "self_state": {
                    "identity_context": "Machina Virtual Brain v0.1",
                    "capabilities": ["durable cognitive loop"],
                    "limitations": ["default cognition is deterministic"],
                },
                "world_state": {
                    "known_facts": [],
                    "observations": [observation.id],
                    "epistemic_status": "observed",
                },
                "uncertainties": [],
            },
            input_refs=[observation.id, goal.id],
            source_refs=[str(source["id"])],
            epistemic_status=EpistemicStatus.INTERPRETED,
            confidence=1.0,
        )

    def _memory_query(self, observation: Artifact, workspace: Artifact, goal: Artifact) -> Artifact:
        return Artifact.create(
            ContractKind.MEMORY_QUERY,
            cycle_id=observation.cycle_id,
            producer="workspace",
            data={
                "query": self._text(observation.data["content"]),
                "context": workspace.data["context"],
                "goal_context": goal.data["description"],
                "memory_types": ["episodic", "semantic", "procedural", "autobiographical"],
                "relevance_threshold": 0.0,
                "confidence_threshold": 0.0,
                "limit": 8,
            },
            input_refs=[workspace.id, observation.id, goal.id],
            source_refs=observation.source_refs,
            epistemic_status=EpistemicStatus.INTERPRETED,
        )

    def _memory_retrieval(self, query: Artifact) -> Artifact:
        result = self.memory.retrieve(query)
        return Artifact.create(
            ContractKind.MEMORY_RETRIEVAL,
            cycle_id=query.cycle_id,
            producer="memory",
            data=result,
            input_refs=[query.id, *result["memory_ids"]],
            source_refs=[
                source
                for match in result["matches"]
                for source in match["provenance"]
            ],
            epistemic_status=EpistemicStatus.INTERPRETED,
        )

    def _cognitive_request(
        self, observation: Artifact, workspace: Artifact, retrieval: Artifact, goal: Artifact
    ) -> Artifact:
        return Artifact.create(
            ContractKind.COGNITIVE_REQUEST,
            cycle_id=observation.cycle_id,
            producer="workspace",
            data={
                "workspace_ref": workspace.id,
                "objective": goal.data["description"],
                "problem": self._text(observation.data["content"]),
                "constraints": goal.data["constraints"],
                "available_evidence": [observation.id, *retrieval.data["memory_ids"]],
                "required_depth": "basic",
            },
            input_refs=[workspace.id, retrieval.id, goal.id, observation.id],
            source_refs=observation.source_refs,
            epistemic_status=EpistemicStatus.INTERPRETED,
        )

    def _cognitive_result(
        self,
        observation: Artifact,
        workspace: Artifact,
        retrieval: Artifact,
        goal: Artifact,
        request: Artifact,
    ) -> Artifact:
        return Artifact.create(
            ContractKind.COGNITIVE_RESULT,
            cycle_id=request.cycle_id,
            producer="cognition",
            data=self.cognition.analyze(
                observation=observation,
                workspace=workspace,
                retrieval=retrieval,
                goal=goal,
                request=request,
            ),
            input_refs=[request.id, observation.id, workspace.id, retrieval.id, goal.id],
            source_refs=observation.source_refs,
            epistemic_status=EpistemicStatus.INFERRED,
            confidence=0.7,
        )

    def _enriched_workspace(self, workspace: Artifact, result: Artifact) -> Artifact:
        data = dict(workspace.data)
        data["cognitive_result_ref"] = result.id
        data["cognitive_state"] = {
            "understanding": result.data["understanding"],
            "uncertainty": result.data["uncertainty"],
        }
        return Artifact.create(
            ContractKind.WORKSPACE_STATE,
            cycle_id=workspace.cycle_id,
            producer="workspace",
            data=data,
            input_refs=[workspace.id, result.id],
            source_refs=workspace.source_refs,
            epistemic_status=EpistemicStatus.INTERPRETED,
            confidence=result.confidence,
        )

    def _decision_request(
        self, goal: Artifact, workspace: Artifact, result: Artifact
    ) -> Artifact:
        return Artifact.create(
            ContractKind.DECISION_REQUEST,
            cycle_id=goal.cycle_id,
            producer="workspace",
            data={
                "workspace_ref": workspace.id,
                "active_goal_ref": goal.id,
                "cognitive_result_refs": [result.id],
                "constraints": goal.data["constraints"],
                "values": workspace.data["self_state"].get("active_values", []),
                "risks": [],
                "permissions": {"default_executor": "acknowledge_only"},
            },
            input_refs=[workspace.id, result.id, goal.id],
            source_refs=workspace.source_refs,
            epistemic_status=EpistemicStatus.INTERPRETED,
        )

    def _decision(
        self, goal: Artifact, workspace: Artifact, result: Artifact, request: Artifact
    ) -> Artifact:
        return Artifact.create(
            ContractKind.DECISION,
            cycle_id=goal.cycle_id,
            producer="agency",
            data=self.agency.decide(
                goal=goal,
                workspace=workspace,
                cognitive_result=result,
                request=request,
            ),
            input_refs=[request.id, goal.id, workspace.id, result.id],
            source_refs=workspace.source_refs,
            epistemic_status=EpistemicStatus.INTERPRETED,
            confidence=0.7,
        )

    def _action_intent(self, goal: Artifact, decision: Artifact) -> Artifact:
        selected = dict(decision.data["selected_plan"])
        return Artifact.create(
            ContractKind.ACTION_INTENT,
            cycle_id=goal.cycle_id,
            producer="agency",
            data={
                "decision_ref": decision.id,
                "goal_ref": goal.id,
                "action": selected["action"],
                "target": selected["target"],
                "parameters": selected["parameters"],
                "expected_outcome": decision.data["expected_outcome"],
                "constraints": goal.data["constraints"],
                "risk_level": decision.data["risk"],
                "authorization": {"granted": True, "scope": "default_executor"},
                "success_criteria": goal.data["success_criteria"],
                "expiration": None,
            },
            input_refs=[decision.id, goal.id],
            source_refs=decision.source_refs,
            epistemic_status=EpistemicStatus.INTERPRETED,
            confidence=decision.confidence,
        )

    def _action_execution(self, intent: Artifact) -> Artifact:
        return Artifact.create(
            ContractKind.ACTION_EXECUTION,
            cycle_id=intent.cycle_id,
            producer="action_system",
            data={"intent_ref": intent.id, "idempotency_key": intent.id},
            input_refs=[intent.id],
            source_refs=intent.source_refs,
            epistemic_status=EpistemicStatus.OBSERVED,
        )

    def _action_result(self, intent: Artifact, execution: Artifact) -> Artifact:
        try:
            result = dict(self.action_executor.execute(intent))
        except Exception as error:
            result = {
                "status": "failed",
                "actual_action": {
                    "action": intent.data["action"],
                    "target": intent.data["target"],
                    "parameters": intent.data["parameters"],
                },
                "observed_result": {"status": "unknown"},
                "errors": [{"type": type(error).__name__, "message": str(error)}],
                "side_effects": [],
                "executed_at": now_utc(),
                "evidence": [],
            }
        result["intent_ref"] = intent.id
        result["execution_ref"] = execution.id
        return Artifact.create(
            ContractKind.ACTION_RESULT,
            cycle_id=intent.cycle_id,
            producer="action_system",
            data=result,
            input_refs=[intent.id, execution.id],
            source_refs=intent.source_refs,
            epistemic_status=EpistemicStatus.OBSERVED,
            confidence=1.0,
        )

    def _experience(
        self, observation: Artifact, workspace: Artifact, intent: Artifact, result: Artifact
    ) -> Artifact:
        expected = intent.data["expected_outcome"]
        outcome_status = result.data["status"]
        return Artifact.create(
            ContractKind.EXPERIENCE,
            cycle_id=observation.cycle_id,
            producer="interaction_loop",
            data={
                "context": workspace.data["context"],
                "observation_refs": [observation.id],
                "action_intent_ref": intent.id,
                "action_result_ref": result.id,
                "expected_outcome": expected,
                "actual_outcome": result.data["observed_result"],
                "prediction_error": 0.0 if outcome_status == "succeeded" else 1.0,
                "consequences": result.data["side_effects"],
                "occurred_at": now_utc(),
            },
            input_refs=[observation.id, workspace.id, intent.id, result.id],
            source_refs=[*observation.source_refs, *result.source_refs],
            epistemic_status=EpistemicStatus.OBSERVED,
            confidence=1.0,
        )

    def _episode_memory(
        self, experience: Artifact, observation: Artifact, intent: Artifact, result: Artifact
    ) -> Artifact:
        return Artifact.create(
            ContractKind.MEMORY_RECORD,
            cycle_id=experience.cycle_id,
            producer="memory",
            data={
                "memory_key": f"episode:{experience.id}",
                "memory_type": "episodic",
                "content": {
                    "experience_ref": experience.id,
                    "observation": observation.data["content"],
                    "action": intent.data["action"],
                    "outcome": result.data["observed_result"],
                    "outcome_status": result.data["status"],
                },
                "evidence_refs": [experience.id, observation.id, intent.id, result.id],
                "confidence": 1.0,
                "importance": 0.5,
                "record_version": 1,
                "supersedes": None,
                "consolidation_state": "recorded",
            },
            input_refs=[experience.id, observation.id, intent.id, result.id],
            source_refs=experience.source_refs,
            epistemic_status=EpistemicStatus.OBSERVED,
            confidence=1.0,
        )

    def _evaluation(self, experience: Artifact, result: Artifact) -> Artifact:
        succeeded = result.data["status"] == "succeeded"
        return Artifact.create(
            ContractKind.EVALUATION,
            cycle_id=experience.cycle_id,
            producer="learning",
            data={
                "experience_ref": experience.id,
                "expected_outcome": experience.data["expected_outcome"],
                "actual_outcome": experience.data["actual_outcome"],
                "outcome_status": result.data["status"],
                "success": succeeded,
                "prediction_error": experience.data["prediction_error"],
                "lessons": [] if succeeded else ["Preserve the failure as evidence; do not generalize success."],
            },
            input_refs=[experience.id, result.id],
            source_refs=experience.source_refs,
            epistemic_status=EpistemicStatus.INTERPRETED,
            confidence=1.0,
        )

    def _learning_proposal(
        self, experience: Artifact, evaluation: Artifact, goal: Artifact, intent: Artifact
    ) -> Artifact:
        confidence = 0.8 if evaluation.data["success"] else 0.4
        return Artifact.create(
            ContractKind.LEARNING_PROPOSAL,
            cycle_id=experience.cycle_id,
            producer="learning",
            data=self.learning.propose(
                experience=experience,
                evaluation=evaluation,
                goal=goal,
                action_intent=intent,
            ),
            input_refs=[experience.id, evaluation.id, goal.id, intent.id],
            source_refs=experience.source_refs,
            epistemic_status=EpistemicStatus.INFERRED,
            confidence=confidence,
            status="pending",
        )

    def _validation(self, proposal: Artifact, evaluation: Artifact) -> Artifact:
        approved = proposal.confidence is not None and proposal.confidence >= 0.7
        memory_key = self._memory_key(proposal)
        previous_version, _ = self.memory.latest_version(memory_key)
        return Artifact.create(
            ContractKind.VALIDATION_RESULT,
            cycle_id=proposal.cycle_id,
            producer="consolidation",
            data={
                "proposal_ref": proposal.id,
                "status": "approved" if approved else "rejected",
                "reason": (
                    "Evidence is sufficient for a versioned memory update."
                    if approved
                    else "Evidence is insufficient; episodic history remains preserved."
                ),
                "base_version": previous_version,
                "target_system": proposal.data["target_system"],
                "memory_key": memory_key,
            },
            input_refs=[proposal.id, evaluation.id],
            source_refs=proposal.source_refs,
            epistemic_status=EpistemicStatus.INTERPRETED,
            confidence=proposal.confidence,
            status="approved" if approved else "rejected",
        )

    def _consolidated_memory(self, proposal: Artifact, validation: Artifact) -> Artifact:
        previous_version, supersedes = self.memory.latest_version(validation.data["memory_key"])
        expected_base = int(validation.data["base_version"])
        if previous_version != expected_base:
            # A concurrent consolidation won.  Preserve the proposal and
            # make the conflict explicit rather than silently overwriting it.
            raise RuntimeError(
                f"memory version conflict: expected {expected_base}, found {previous_version}"
            )
        return Artifact.create(
            ContractKind.MEMORY_RECORD,
            cycle_id=proposal.cycle_id,
            producer="memory",
            data={
                "memory_key": validation.data["memory_key"],
                "memory_type": "semantic",
                "content": proposal.data["proposed_change"],
                "evidence_refs": proposal.data["evidence_refs"],
                "confidence": proposal.confidence,
                "importance": 0.6,
                "record_version": previous_version + 1,
                "supersedes": supersedes,
                "consolidation_state": "consolidated",
            },
            input_refs=[proposal.id, validation.id, *proposal.data["evidence_refs"]],
            source_refs=proposal.source_refs,
            epistemic_status=EpistemicStatus.BELIEVED,
            confidence=proposal.confidence,
            status="consolidated",
        )

    def _model_update(
        self, proposal: Artifact, validation: Artifact, memory: Artifact
    ) -> Artifact:
        return Artifact.create(
            ContractKind.MODEL_UPDATE,
            cycle_id=proposal.cycle_id,
            producer="consolidation",
            data={
                "target": proposal.data["target_system"],
                "previous_version": validation.data["base_version"],
                "new_version": memory.data["record_version"],
                "change": proposal.data["proposed_change"],
                "evidence_refs": proposal.data["evidence_refs"],
                "reason": validation.data["reason"],
                "created_by": "consolidation",
            },
            input_refs=[proposal.id, validation.id, memory.id],
            source_refs=proposal.source_refs,
            epistemic_status=EpistemicStatus.BELIEVED,
            confidence=proposal.confidence,
            status="committed",
        )

    def _completed_status(
        self,
        cycle_id: str,
        experience: Artifact,
        episode: Artifact,
        proposal: Artifact,
        validation: Artifact,
    ) -> Artifact:
        return Artifact.create(
            ContractKind.CYCLE_STATUS,
            cycle_id=cycle_id,
            producer="orchestrator",
            data={
                "status": "completed",
                "checkpoint": "cycle.completed",
                "experience_ref": experience.id,
                "episode_memory_ref": episode.id,
                "learning_proposal_ref": proposal.id,
                "validation_ref": validation.id,
            },
            input_refs=[experience.id, episode.id, proposal.id, validation.id],
            source_refs=experience.source_refs,
            epistemic_status=EpistemicStatus.OBSERVED,
        )

    def _record_failure(self, cycle_id: str, error: Exception) -> None:
        # If persistence itself is broken, a second append would only obscure
        # the original error.  Otherwise record the failure as an artifact so
        # resumption has an explicit audit point.
        try:
            failure = Artifact.create(
                ContractKind.FAILURE,
                cycle_id=cycle_id,
                producer="orchestrator",
                data={
                    "stage": self._last_stage(cycle_id),
                    "error_type": type(error).__name__,
                    "message": str(error),
                },
                epistemic_status=EpistemicStatus.OBSERVED,
                status="failed",
            )
            self.store.append("cycle.failed", failure)
        except Exception:
            pass

    def _stop_if_requested(
        self, cycle_id: str, checkpoint: str, requested: str | None
    ) -> bool:
        if requested != checkpoint:
            return False
        self.pause(cycle_id, checkpoint=checkpoint, reason="stop_after checkpoint")
        return True

    def _required(self, cycle_id: str, event_type: str) -> Artifact:
        artifact = self.store.latest_artifact(cycle_id, event_type)
        if artifact is None:
            raise RuntimeError(f"cycle {cycle_id} lacks required event {event_type}")
        return artifact

    def _require_cycle(self, cycle_id: str) -> None:
        if not self.store.has_cycle(cycle_id):
            raise CycleNotFoundError(cycle_id)

    def _last_stage(self, cycle_id: str) -> str:
        events = self.store.events_for_cycle(cycle_id)
        return events[-1].event_type if events else "cycle.initialization"

    def _result(self, cycle_id: str) -> CycleResult:
        events = tuple(self.store.events_for_cycle(cycle_id))
        observation = self._required(cycle_id, "observation.received")
        goal = self._required(cycle_id, "goal.activated")
        experience = self.store.latest_artifact(cycle_id, "experience.created")
        update = self.store.latest_artifact(cycle_id, "model.updated")
        status = "completed" if self.store.latest_artifact(cycle_id, "cycle.completed") else "incomplete"
        return CycleResult(
            cycle_id=cycle_id,
            status=status,
            events=events,
            observation_id=observation.id,
            goal_id=goal.id,
            experience_id=experience.id if experience else None,
            model_update_id=update.id if update else None,
        )

    @staticmethod
    def _goal_data(
        objective: str | Mapping[str, Any],
        *,
        constraints: Sequence[str],
        success_criteria: Sequence[str],
        priority: int,
    ) -> dict[str, Any]:
        if isinstance(objective, str):
            return {
                "description": objective,
                "priority": priority,
                "constraints": list(constraints),
                "success_criteria": list(success_criteria),
            }
        data = dict(objective)
        data.setdefault("priority", priority)
        data.setdefault("constraints", list(constraints))
        data.setdefault("success_criteria", list(success_criteria))
        if not data.get("description"):
            raise ValueError("goal mapping must include a non-empty description")
        return data

    @staticmethod
    def _memory_key(proposal: Artifact) -> str:
        lesson = proposal.data["proposed_change"]
        statement = lesson.get("statement", "outcome") if isinstance(lesson, Mapping) else str(lesson)
        normalized = "".join(character.lower() for character in statement if character.isalnum())
        return f"lesson:{normalized[:96] or 'outcome'}"

    @staticmethod
    def _text(value: Any) -> str:
        if isinstance(value, str):
            return value
        import json

        return json.dumps(value, ensure_ascii=False, sort_keys=True)
