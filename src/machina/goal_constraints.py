"""Explicit goal compatibility and shared-resource assessment.

Assessments are advisory: they never pause, complete, or execute goals.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Mapping, Any
from itertools import combinations

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



    def schedule(
        self,
        goal_ids: tuple[str, ...] | list[str],
        *,
        utilities: Mapping[str, float] | None = None,
        resource_costs: Mapping[str, Mapping[str, float]] | None = None,
        resource_limits: Mapping[str, float] | None = None,
    ) -> "GoalSchedule":
        """Choose the highest-utility feasible subset; never changes goal state."""
        return _schedule(
            self, goal_ids, utilities=utilities,
            resource_costs=resource_costs, resource_limits=resource_limits,
        )


@dataclass(frozen=True, slots=True)
class GoalSchedule:
    """Best feasible subset under explicit utilities, constraints, and budgets."""

    selected_goal_ids: tuple[str, ...]
    deferred_goal_ids: tuple[str, ...]
    total_utility: float
    assessment: GoalConstraintAssessment
    rationale: str

    def to_dict(self) -> dict[str, object]:
        return {
            "selected_goal_ids": list(self.selected_goal_ids),
            "deferred_goal_ids": list(self.deferred_goal_ids),
            "total_utility": self.total_utility,
            "assessment": self.assessment.to_dict(),
            "rationale": self.rationale,
        }


def _schedule(
    resolver: GoalConflictResolver,
    goal_ids: tuple[str, ...] | list[str],
    *,
    utilities: Mapping[str, float] | None = None,
    resource_costs: Mapping[str, Mapping[str, float]] | None = None,
    resource_limits: Mapping[str, float] | None = None,
) -> GoalSchedule:
    ids = tuple(goal_ids)
    if not ids or len(ids) > 16:
        raise ValueError("scheduling requires between 1 and 16 candidate goals")
    if len(set(ids)) != len(ids) or any(not isinstance(x, str) or not x.strip() for x in ids):
        raise ValueError("goal_ids must be unique non-empty strings")
    utility_map: dict[str, float] = {}
    for key, value in (utilities or {}).items():
        if key not in ids or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("utilities must be finite, non-negative, and refer to candidate goals")
        utility_map[key] = float(value)
    records = resolver.store.ranked_open_goals(limit=1000)
    stored = {item["goal_id"]: float(item["priority"]) for item in records}
    for goal_id in ids:
        utility_map.setdefault(goal_id, stored.get(goal_id, 0.5))
    relations = resolver.store.goal_relations()
    supports = [
        item for item in relations
        if item["relation"] == "supports"
        and item["source_goal_id"] in ids and item["target_goal_id"] in ids
    ]
    best: tuple[str, ...] = ()
    best_score = -1.0
    best_assessment: GoalConstraintAssessment | None = None
    # Enumerate feasible subsets. Stable lexical tie-break makes the result reproducible.
    for size in range(1, len(ids) + 1):
        for subset in combinations(sorted(ids), size):
            subset_costs = {
                goal_id: resources
                for goal_id, resources in (resource_costs or {}).items()
                if goal_id in subset
            }
            selected_subset = set(subset)
            explicit_conflict = any(
                item["relation"] == "conflicts"
                and item["source_goal_id"] in selected_subset
                and item["target_goal_id"] in selected_subset
                for item in relations
            )
            if explicit_conflict:
                continue
            assessment = resolver.assess(
                subset, resource_costs=subset_costs, resource_limits=resource_limits
            )
            if not assessment.compatible:
                continue
            selected = set(subset)
            score = sum(utility_map[item] for item in subset)
            score += sum(
                float(item["strength"])
                for item in supports
                if item["source_goal_id"] in selected and item["target_goal_id"] in selected
            )
            if score > best_score or (score == best_score and subset < best):
                best, best_score, best_assessment = subset, score, assessment
    if best_assessment is None:
        # Empty selection is safer than returning an infeasible combination.
        best_assessment = resolver.assess(
            ids[:1], resource_costs=resource_costs, resource_limits=resource_limits
        )
        if best_assessment.compatible:
            best, best_score = (), 0.0
        else:
            raise ValueError("no feasible goal subset exists, including individual candidates")
    deferred = tuple(item for item in sorted(ids) if item not in set(best))
    return GoalSchedule(
        selected_goal_ids=best,
        deferred_goal_ids=deferred,
        total_utility=best_score,
        assessment=best_assessment,
        rationale=(
            "Subconjunto viável com maior utilidade explícita; objetivos adiados "
            "permanecem abertos. Empates são resolvidos pela ordem lexical."
        ),
    )
