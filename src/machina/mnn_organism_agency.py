"""Memory-guided Agency policy for the integrated MNN organism."""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from .components import AgencyPolicy, FirstCandidateAgency
from .contracts import Artifact
from .mnn_organism import DecisionOption, MemoryGuidance, MNNOrganism


class MNNOrganismAgencyAdapter:
    """Score existing plans using bounded, attributable recalled evidence.

    This adapter cannot invent or execute actions. With no relevant memory it
    returns the wrapped policy's original selection unchanged.
    """

    def __init__(
        self,
        organism: MNNOrganism,
        *,
        target_unit: str,
        base_policy: AgencyPolicy | None = None,
        memory_weight: float = 0.25,
        limit: int = 5,
    ) -> None:
        if not isinstance(organism, MNNOrganism):
            raise TypeError("organism must be an MNNOrganism")
        if target_unit not in organism.network.units:
            raise ValueError(f"unknown memory guidance target unit: {target_unit}")
        if isinstance(memory_weight, bool) or not isinstance(memory_weight, (int, float)):
            raise ValueError("memory_weight must be within [0, 1]")
        if not math.isfinite(memory_weight) or not 0.0 <= memory_weight <= 1.0:
            raise ValueError("memory_weight must be within [0, 1]")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        self.organism = organism
        self.target_unit = target_unit
        self.base_policy = base_policy or FirstCandidateAgency()
        self.memory_weight = float(memory_weight)
        self.limit = limit

    @staticmethod
    def _query(plan: Mapping[str, Any]) -> str:
        parts = (
            plan.get("action", ""),
            plan.get("target", ""),
            plan.get("expected_outcome", ""),
            plan.get("memory_query", ""),
            plan.get("parameters", {}),
        )
        return " ".join(
            part if isinstance(part, str) else str(part)
            for part in parts if part is not None
        )

    def apply_selected_memory_feedback(
        self,
        decision: Mapping[str, Any],
        outcomes: Mapping[str, bool],
        *,
        context: str,
        operation_id: str,
        strength: float = 0.10,
    ) -> tuple[dict[str, float], bool]:
        """Apply explicit, idempotent feedback only to evidence used by this decision.

        The caller supplies usefulness labels after evaluating the action.
        This method does not infer memory usefulness from action success, and
        cannot rate evidence retrieved for an unselected candidate.
        """
        if self.organism.memory is None:
            raise RuntimeError("no FragmentMemory is attached to this organism")
        if not isinstance(decision, Mapping):
            raise ValueError("decision must be a mapping")
        rationale = decision.get("rationale", {})
        guidance_data = rationale.get("memory_guidance", {}) if isinstance(rationale, Mapping) else {}
        if not isinstance(guidance_data, Mapping) or guidance_data.get("status") != "applied":
            raise ValueError("decision has no applied memory guidance")
        selected_ids = guidance_data.get("selected_evidence_ids", [])
        if not isinstance(selected_ids, list) or not selected_ids:
            raise ValueError("decision has no selected memory evidence")
        if not isinstance(outcomes, Mapping) or not outcomes:
            raise ValueError("outcomes must be a non-empty mapping")
        unknown = set(outcomes) - set(selected_ids)
        if unknown:
            raise ValueError(
                "feedback may only rate evidence used by the selected candidate: "
                + ", ".join(sorted(unknown))
            )
        signal_map = guidance_data.get("memory_signals", {})
        selected_key = guidance_data.get("selected_candidate")
        signal = signal_map.get(selected_key, 0.0) if isinstance(signal_map, Mapping) else 0.0
        guidance = MemoryGuidance(
            query=str(context),
            target_unit=self.target_unit,
            signal=float(signal),
            evidence_ids=tuple(selected_ids),
            evidence_scores={fragment_id: float(signal) for fragment_id in selected_ids},
        )
        return self.organism.evaluate_memory_guidance(
            guidance, outcomes, context=context,
            operation_id=operation_id, strength=strength,
        )

    def decide(
        self, *, goal: Artifact, workspace: Artifact,
        cognitive_result: Artifact, request: Artifact,
    ) -> Mapping[str, Any]:
        base = dict(self.base_policy.decide(
            goal=goal, workspace=workspace,
            cognitive_result=cognitive_result, request=request,
        ))
        plans = cognitive_result.data.get("candidate_plans", [])
        if self.organism.memory is None or not isinstance(plans, list) or len(plans) < 2:
            rationale = dict(base.get("rationale", {}))
            rationale["memory_guidance"] = {
                "status": "not_applied",
                "reason": "no_fragment_memory" if self.organism.memory is None
                else "fewer_than_two_candidate_plans",
                "memory_weight": self.memory_weight,
            }
            base["rationale"] = rationale
            return base

        options: list[DecisionOption] = []
        plan_by_key: dict[str, Mapping[str, Any]] = {}
        for index, raw in enumerate(plans):
            if not isinstance(raw, Mapping):
                raise ValueError("candidate plans must be mappings")
            plan = dict(raw)
            key = f"{index:06d}:{plan.get('plan_id', plan.get('action', 'candidate'))}"
            utility = plan.get("base_utility", plan.get("utility", 0.0))
            if isinstance(utility, bool) or not isinstance(utility, (int, float)) or not math.isfinite(utility):
                raise ValueError(f"candidate {key} has invalid base utility")
            options.append(DecisionOption(
                action=key, base_utility=float(utility), memory_query=self._query(plan)
            ))
            plan_by_key[key] = plan

        assessment = self.organism.assess_decisions(
            options, target_unit=self.target_unit,
            context=str(goal.data["description"]),
            memory_weight=self.memory_weight, limit=self.limit,
        )
        evidence = {key: list(ids) for key, ids in assessment.evidence_ids.items()}
        if not any(evidence.values()):
            rationale = dict(base.get("rationale", {}))
            rationale["memory_guidance"] = {
                "status": "no_relevant_evidence",
                "memory_weight": self.memory_weight,
                "candidate_scores": dict(assessment.scores),
                "base_utilities": dict(assessment.base_utilities),
                "memory_signals": dict(assessment.memory_signals),
                "evidence_ids": evidence,
            }
            base["rationale"] = rationale
            return base

        selected_key = assessment.selected_action
        selected = dict(plan_by_key[selected_key])
        rationale = dict(base.get("rationale", {}))
        rationale["base_policy"] = rationale.get("policy", type(self.base_policy).__name__)
        rationale["policy"] = type(self).__name__
        rationale["memory_guidance"] = {
            "status": "applied",
            "target_unit": self.target_unit,
            "memory_weight": self.memory_weight,
            "selected_candidate": selected_key,
            "candidate_scores": dict(assessment.scores),
            "base_utilities": dict(assessment.base_utilities),
            "memory_signals": dict(assessment.memory_signals),
            "evidence_ids": evidence,
            "selected_evidence_ids": evidence[selected_key],
            "method": "confidence_weighted_lexical_overlap",
            "interpretation": "bounded recalled evidence, not a command or semantic proof",
        }
        return {
            **base,
            "selected_option": selected,
            "selected_plan": selected,
            "expected_outcome": selected.get("expected_outcome", base.get("expected_outcome", "")),
            "risk": selected.get("risk", base.get("risk", "unknown")),
            "reversibility": selected.get("reversibility", base.get("reversibility", "unknown")),
            "rationale": rationale,
        }
