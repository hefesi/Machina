"""Coordinate evidence-backed curiosity proposals with bounded autonomy.

This module composes existing Phase 4 components. It deliberately does not
introduce a second curiosity scoring policy or execute the selected goal.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Mapping

from .autonomy import AutonomyContext, AutonomyController, AutonomyDecision, GoalCandidate
from .curiosity import CuriosityInvestigationStore
from .curiosity_policy import CuriosityDecision, CuriosityQuestion, CuriositySelector
from .homeostasis import HomeostaticProposal
from .self_model_learning import SelfModelLearningBridge


_NO_HYPOTHESIS = (
    "No explicit hypothesis was supplied; investigate the knowledge gap "
    "without presuming an explanation."
)


def _bounded(name: str, value: Any, lower: float, upper: float) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
    ):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not lower <= result <= upper:
        raise ValueError(f"{name} must be within [{lower}, {upper}]")
    return result


class CuriosityGoalCoordinator:
    """Join self-model gaps, curiosity ranking, homeostasis and goal selection.

    The coordinator reuses SelfModelLearningBridge for evidence/status gating,
    curiosity_policy.CuriositySelector for exploration ranking, and
    AutonomyController for the final bounded goal decision. A selected
    investigation is persisted only when autonomy also selects that curiosity
    goal. No goal is executed and no external action is authorized here.
    """

    def __init__(
        self,
        bridge: SelfModelLearningBridge,
        controller: AutonomyController,
        selector: CuriositySelector | None = None,
    ) -> None:
        if not isinstance(bridge, SelfModelLearningBridge):
            raise TypeError("bridge must be a SelfModelLearningBridge")
        if not isinstance(controller, AutonomyController):
            raise TypeError("controller must be an AutonomyController")
        if selector is not None and not isinstance(selector, CuriositySelector):
            raise TypeError("selector must be a CuriositySelector")
        self.bridge = bridge
        self.controller = controller
        self.selector = selector or CuriositySelector()

    @staticmethod
    def _homeostatic_pressure(
        proposal: HomeostaticProposal,
        *,
        persistence_horizon: int,
    ) -> float:
        if not isinstance(proposal.deviations, Mapping):
            raise ValueError("homeostatic deviations must be a mapping")
        if not isinstance(proposal.persistence, Mapping):
            raise ValueError("homeostatic persistence must be a mapping")
        pressure = 0.0
        for name, raw_deviation in proposal.deviations.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("homeostatic deviation names must be non-empty")
            deviation = _bounded(f"deviations[{name}]", raw_deviation, -1.0, 1.0)
            count = proposal.persistence.get(name, 0)
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(f"persistence[{name}] must be a non-negative integer")
            persistence_factor = min(1.0, count / persistence_horizon)
            pressure = max(pressure, abs(deviation) * persistence_factor)
        return pressure

    @staticmethod
    def _merge_drive_adjustments(
        *sources: Mapping[str, float],
    ) -> dict[str, float]:
        combined: dict[str, float] = {}
        for source in sources:
            if not isinstance(source, Mapping):
                raise ValueError("drive adjustments must be mappings")
            for drive, raw_value in source.items():
                if not isinstance(drive, str) or not drive.strip():
                    raise ValueError("drive adjustment names must be non-empty")
                value = _bounded(f"drive_adjustments[{drive}]", raw_value, -0.3, 0.3)
                combined[drive] = max(-0.3, min(0.3, combined.get(drive, 0.0) + value))
        return combined

    def deliberate(
        self,
        gap_mappings: Mapping[str, Mapping[str, Any]],
        *,
        cycle_id: str,
        investigation_store: CuriosityInvestigationStore,
        context: AutonomyContext | None = None,
        motivation: Any | None = None,
        homeostatic_proposal: HomeostaticProposal | None = None,
        stability_pressure: float | None = None,
        homeostatic_persistence_horizon: int = 3,
        include_inferred: bool = True,
        maximum_belief_confidence: float = 0.65,
        recent_goal_ids: Iterable[str] = (),
        investigation_id: str | None = None,
    ) -> dict[str, Any]:
        """Rank and select one goal, then persist a selected curiosity inquiry.

        Homeostatic pressure is a transparent heuristic: the largest absolute
        observed deviation is multiplied by its persistence fraction. An
        explicit stability_pressure overrides that derived scalar. Homeostatic
        and temporal motivational adjustments are combined and bounded before
        being passed to AutonomyController.
        """
        if not isinstance(cycle_id, str) or not cycle_id.strip():
            raise ValueError("cycle_id must be a non-empty string")
        if not isinstance(investigation_store, CuriosityInvestigationStore):
            raise TypeError("investigation_store must be a CuriosityInvestigationStore")
        if context is not None and not isinstance(context, AutonomyContext):
            raise TypeError("context must be an AutonomyContext")
        if isinstance(homeostatic_persistence_horizon, bool) or not isinstance(homeostatic_persistence_horizon, int) or homeostatic_persistence_horizon < 1:
            raise ValueError("homeostatic_persistence_horizon must be a positive integer")
        recent = tuple(recent_goal_ids)
        if any(not isinstance(item, str) or not item.strip() for item in recent):
            raise ValueError("recent_goal_ids must contain non-empty strings")

        homeostatic_adjustments: Mapping[str, float] = {}
        derived_pressure = 0.0
        if homeostatic_proposal is not None:
            if not isinstance(homeostatic_proposal, HomeostaticProposal):
                raise TypeError("homeostatic_proposal must be a HomeostaticProposal")
            if homeostatic_proposal.cycle_id != cycle_id:
                raise ValueError("homeostatic proposal cycle_id must match the deliberation cycle")
            homeostatic_adjustments = homeostatic_proposal.adjustments
            derived_pressure = self._homeostatic_pressure(
                homeostatic_proposal,
                persistence_horizon=homeostatic_persistence_horizon,
            )

        if stability_pressure is None:
            selected_pressure = derived_pressure
            pressure_source = "homeostasis" if homeostatic_proposal is not None else "default"
        else:
            selected_pressure = _bounded("stability_pressure", stability_pressure, 0.0, 1.0)
            pressure_source = "explicit"

        motivational_adjustments: Mapping[str, float] = {}
        motivational_goals: list[GoalCandidate] = []
        if motivation is not None:
            if not callable(getattr(motivation, "temporal_urgencies", None)):
                raise ValueError("motivation must expose temporal_urgencies()")
            pressures = motivation.temporal_urgencies()
            if not isinstance(pressures, Mapping):
                raise ValueError("temporal_urgencies() must return a mapping")
            motivational_adjustments = {
                drive: (_bounded(f"temporal_urgencies[{drive}]", pressure, 0.0, 1.0) - 0.5) * 0.3
                for drive, pressure in pressures.items()
                if isinstance(drive, str) and drive.strip()
            }
            if len(motivational_adjustments) != len(pressures):
                raise ValueError("temporal urgency drive names must be non-empty strings")
            motivational_goals = self.controller.generate_motivational_goals(motivation)

        drive_adjustments = self._merge_drive_adjustments(
            homeostatic_adjustments,
            motivational_adjustments,
        )

        proposals = self.bridge.propose_curiosity_goals(
            gap_mappings,
            include_inferred=include_inferred,
            maximum_belief_confidence=maximum_belief_confidence,
            investigation_store=investigation_store,
        )
        provenance_by_goal = {
            item["goal_id"]: item for item in proposals["provenance"]
        }
        questions: list[CuriosityQuestion] = []
        for item in proposals["provenance"]:
            spec = gap_mappings[item["belief_property"]]
            hypothesis = spec.get("hypothesis", _NO_HYPOTHESIS)
            if not isinstance(hypothesis, str) or not hypothesis.strip():
                raise ValueError("hypothesis must be a non-empty string when supplied")
            questions.append(CuriosityQuestion(
                question_id=item["goal_id"],
                gap_property=item["belief_property"],
                question=item["question"],
                hypothesis=hypothesis.strip(),
                uncertainty=1.0 - item["belief_confidence"],
                expected_information_gain=item["information_gain"],
                relevance=item["impact"],
                # The store suppressed prior questions before this point, so
                # novelty is explicitly the binary "not previously recorded".
                novelty=1.0,
                estimated_cost=item["estimated_cost"],
                risk=item["risk"],
                requires_external_action=False,
            ))

        curiosity_decision: CuriosityDecision = self.selector.choose(
            questions,
            stability_pressure=selected_pressure,
            recent_question_ids=recent,
            allow_external_actions=False,
        )
        curiosity_goal: GoalCandidate | None = None
        if curiosity_decision.selected is not None:
            selected_id = curiosity_decision.selected.question_id
            curiosity_goal = next(
                goal for goal in proposals["goals"] if goal.goal_id == selected_id
            )

        candidates: list[GoalCandidate] = []
        if context is not None:
            candidates.extend(self.controller.generate_goals(context))
        candidates.extend(motivational_goals)
        if curiosity_goal is not None:
            candidates.append(curiosity_goal)

        by_id: dict[str, GoalCandidate] = {}
        for candidate in candidates:
            if candidate.goal_id in by_id:
                raise ValueError(f"duplicate goal_id across deliberation sources: {candidate.goal_id}")
            by_id[candidate.goal_id] = candidate

        autonomy_decision: AutonomyDecision = self.controller.choose(
            by_id.values(),
            drive_adjustments=drive_adjustments,
            recent_goal_ids=recent,
        )
        selected_goal = autonomy_decision.selected_goal
        selected_provenance = (
            provenance_by_goal.get(selected_goal.goal_id) if selected_goal else None
        )
        investigation = None
        if selected_goal is not None and selected_provenance is not None:
            selected_question = curiosity_decision.selected
            assert selected_question is not None
            score = next(
                item["score"]["total"]
                for item in curiosity_decision.ranked
                if item["question"]["question_id"] == selected_goal.goal_id
            )
            spec = gap_mappings[selected_provenance["belief_property"]]
            hypothesis = spec.get("hypothesis", _NO_HYPOTHESIS).strip()
            selected_investigation_id = investigation_id or f"{cycle_id}:{selected_goal.goal_id}"
            evidence_ref = selected_provenance.get("belief_evidence_ref") or "none"
            investigation = investigation_store.start_investigation(
                selected_investigation_id,
                gap_property=selected_provenance["belief_property"],
                question=selected_provenance["question"],
                hypothesis=hypothesis,
                selection_reason=(
                    f"CuriositySelector score={score:.6f}; "
                    f"stability_pressure={selected_pressure:.6f}; "
                    f"belief_status={selected_provenance['belief_status']}; "
                    f"belief_evidence_ref={evidence_ref}"
                ),
                cycle_id=cycle_id,
                goal_id=selected_goal.goal_id,
            )

        return {
            "proposals": proposals,
            "curiosity_decision": curiosity_decision,
            "autonomy_decision": autonomy_decision,
            "selected_goal_id": selected_goal.goal_id if selected_goal else None,
            "selected_provenance": selected_provenance,
            "curiosity_candidate_goal_id": curiosity_goal.goal_id if curiosity_goal else None,
            "curiosity_goal_selected": investigation is not None,
            "investigation": investigation,
            "stability_pressure": selected_pressure,
            "stability_pressure_source": pressure_source,
            "drive_adjustments": drive_adjustments,
            "execution_performed": False,
        }
