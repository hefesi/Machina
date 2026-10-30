"""Explicit goal compatibility and shared-resource assessment.

Assessments are advisory: they never pause, complete, or execute goals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Mapping

from .goal_store import PersistentGoalStore


@dataclass(frozen=True, slots=True)
class GoalConstraintAssessment:
    goal_ids: tuple[str, ...]
    compatible: bool
    recommendation: str
    conflicts: tuple[dict[str, object], ...]
    missing_requirements: tuple[dict[str, object], ...]
    resource_totals: dict[str, float]
    resource_limits: dict[str, float]
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class GoalConflictResolver:
    """Evaluate a proposed set of goals against explicit relations and budgets."""

    def __init__(self, store: PersistentGoalStore) -> None:
        self.store = store

    def assess(
        self,
        goal_ids: tuple[str, ...] | list[str],
        *,
        resource_costs: Mapping[str, Mapping[str, float]] | None = None,
        resource_limits: Mapping[str, float] | None = None,
    ) -> GoalConstraintAssessment:
        ids = tuple(goal_ids)
        if not ids or any(not isinstance(item, str) or not item.strip() for item in ids):
            raise ValueError("goal_ids must contain non-empty strings")
        if len(set(ids)) != len(ids):
            raise ValueError("goal_ids must be unique")
        costs = resource_costs or {}
        limits = resource_limits or {}
        normalized_costs: dict[str, dict[str, float]] = {}
        normalized_limits: dict[str, float] = {}
        for goal_id, resources in costs.items():
            if goal_id not in ids or not isinstance(resources, Mapping):
                raise ValueError("resource costs must refer only to assessed goals")
            normalized_costs[goal_id] = {}
            for resource, amount in resources.items():
                if not isinstance(resource, str) or not resource.strip():
                    raise ValueError("resource names must be non-empty strings")
                if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
                    raise ValueError("resource costs must be finite and non-negative")
                normalized_costs[goal_id][resource] = float(amount)
        for resource, amount in limits.items():
            if not isinstance(resource, str) or not resource.strip():
                raise ValueError("resource limit names must be non-empty strings")
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
                raise ValueError("resource limits must be finite and non-negative")
            normalized_limits[resource] = float(amount)

        selected = set(ids)
        conflicts: list[dict[str, object]] = []
        missing: list[dict[str, object]] = []
        totals: dict[str, float] = {}
        for relation in self.store.goal_relations():
            source, target = relation["source_goal_id"], relation["target_goal_id"]
            kind = relation["relation"]
            if kind == "conflicts" and source in selected and target in selected:
                conflicts.append(relation)
            elif kind == "requires" and source in selected and target not in selected:
                missing.append(relation)
        for goal_id, resources in normalized_costs.items():
            for resource, amount in resources.items():
                totals[resource] = totals.get(resource, 0.0) + amount
        exceeded = {
            resource: total for resource, total in totals.items()
            if resource in normalized_limits and total > normalized_limits[resource]
        }
        compatible = not conflicts and not missing and not exceeded
        if conflicts:
            recommendation = "prioritize_one"
            rationale = "Há relações explícitas de conflito entre objetivos selecionados."
        elif missing:
            recommendation = "needs_dependency"
            rationale = "Um ou mais objetivos dependem de objetivos não incluídos."
        elif exceeded:
            recommendation = "defer_or_reallocate"
            rationale = "O custo agregado excede um ou mais limites de recursos declarados."
        else:
            recommendation = "co_select"
            rationale = "Nenhum conflito, requisito ausente ou limite excedido foi encontrado nos dados fornecidos."
        if exceeded:
            rationale += " Recursos excedidos: " + ", ".join(sorted(exceeded))
        return GoalConstraintAssessment(
            goal_ids=ids,
            compatible=compatible,
            recommendation=recommendation,
            conflicts=tuple(conflicts),
            missing_requirements=tuple(missing),
            resource_totals=totals,
            resource_limits=normalized_limits,
            rationale=rationale,
        )
