"""Bounded curiosity-driven goal prioritization for Phase 4.

The selector proposes internal investigations from caller-supplied evidence
signals. It does not perform research or claim subjective desire.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any, Iterable


def _unit(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return float(value)


@dataclass(frozen=True, slots=True)
class CuriosityQuestion:
    question_id: str
    gap_property: str
    question: str
    hypothesis: str
    uncertainty: float
    expected_information_gain: float
    relevance: float
    novelty: float
    estimated_cost: float
    risk: float = 0.0
    requires_external_action: bool = False

    def __post_init__(self) -> None:
        for field in ("question_id", "gap_property", "question", "hypothesis"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field} must be a non-empty string")
        for field in ("uncertainty", "expected_information_gain", "relevance",
                      "novelty", "estimated_cost", "risk"):
            _unit(field, getattr(self, field))
        if not isinstance(self.requires_external_action, bool):
            raise ValueError("requires_external_action must be a boolean")


@dataclass(frozen=True, slots=True)
class CuriosityDecision:
    selected: CuriosityQuestion | None
    ranked: tuple[dict[str, Any], ...]
    rejected: tuple[dict[str, str], ...]
    exploration_weight: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "selected": asdict(self.selected) if self.selected else None,
            "ranked": [dict(item) for item in self.ranked],
            "rejected": [dict(item) for item in self.rejected],
            "exploration_weight": self.exploration_weight,
            "interpretation": "Bounded operational curiosity; not evidence of subjective experience.",
        }


class CuriositySelector:
    """Rank information-seeking goals while balancing exploration and stability."""

    def __init__(self, *, max_risk: float = 0.35, min_score: float = 0.15) -> None:
        self.max_risk = _unit("max_risk", max_risk)
        self.min_score = _unit("min_score", min_score)

    @staticmethod
    def _score(question: CuriosityQuestion, exploration_weight: float) -> dict[str, float]:
        information_value = question.uncertainty * question.expected_information_gain
        parts = {
            "uncertainty_information_gain": 0.34 * exploration_weight * information_value,
            "relevance": 0.24 * question.relevance,
            "novelty": 0.18 * exploration_weight * question.novelty,
            "stability_value": 0.12 * (1.0 - question.risk),
            "cost_penalty": -0.12 * question.estimated_cost,
            "risk_penalty": -0.45 * question.risk,
        }
        parts["total"] = sum(parts.values())
        parts["information_value_raw"] = information_value
        return parts

    def choose(
        self,
        candidates: Iterable[CuriosityQuestion],
        *,
        stability_pressure: float = 0.0,
        recent_question_ids: Iterable[str] = (),
        allow_external_actions: bool = False,
    ) -> CuriosityDecision:
        stability = _unit("stability_pressure", stability_pressure)
        if not isinstance(allow_external_actions, bool):
            raise ValueError("allow_external_actions must be a boolean")
        exploration_weight = 1.0 - 0.75 * stability
        questions = list(candidates)
        if any(not isinstance(q, CuriosityQuestion) for q in questions):
            raise TypeError("candidates must contain only CuriosityQuestion values")
        if len({q.question_id for q in questions}) != len(questions):
            raise ValueError("question_id values must be unique")
        recent = set(recent_question_ids)
        ranked, rejected = [], []
        for question in questions:
            if question.risk > self.max_risk:
                rejected.append({"question_id": question.question_id, "reason": "risk_above_limit"})
                continue
            if question.requires_external_action and not allow_external_actions:
                rejected.append({"question_id": question.question_id, "reason": "external_action_not_authorized"})
                continue
            score = self._score(question, exploration_weight)
            score["repetition_penalty"] = -0.10 if question.question_id in recent else 0.0
            score["total"] += score["repetition_penalty"]
            ranked.append({"question": asdict(question), "score": score})
        ranked.sort(key=lambda item: (-item["score"]["total"], item["question"]["question_id"]))
        selected = None
        if ranked and ranked[0]["score"]["total"] >= self.min_score:
            selected_id = ranked[0]["question"]["question_id"]
            selected = next(q for q in questions if q.question_id == selected_id)
        elif ranked:
            rejected.append({"question_id": ranked[0]["question"]["question_id"], "reason": "below_minimum_utility"})
        return CuriosityDecision(selected, tuple(ranked), tuple(rejected), exploration_weight)
