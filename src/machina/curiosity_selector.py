"""Evidence-aware ranking of internally proposed knowledge gaps.

The selector ranks caller-supplied proposals. It does not invent questions,
retrieve evidence, perform research, or execute external actions.
Scores are bounded engineering heuristics, not measurements of subjective
curiosity or consciousness.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable


def _unit_interval(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    result = float(value)
    if not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be within [0, 1]")
    return result


@dataclass(frozen=True, slots=True)
class CuriosityCandidate:
    """One proposed knowledge gap with explicit estimates and provenance."""

    candidate_id: str
    gap_property: str
    question: str
    hypothesis: str
    uncertainty: float
    expected_information_gain: float
    relevance: float
    novelty: float
    estimated_cost: float
    risk: float
    evidence_refs: tuple[str, ...] = ()
    requires_external_action: bool = False

    def __post_init__(self) -> None:
        for name in ("candidate_id", "gap_property", "question", "hypothesis"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        for name in (
            "uncertainty", "expected_information_gain", "relevance",
            "novelty", "estimated_cost", "risk",
        ):
            _unit_interval(name, getattr(self, name))
        if not isinstance(self.requires_external_action, bool):
            raise ValueError("requires_external_action must be a boolean")
        if isinstance(self.evidence_refs, (str, bytes)) or not isinstance(self.evidence_refs, tuple):
            raise ValueError("evidence_refs must be a tuple of non-empty strings")
        if any(not isinstance(ref, str) or not ref.strip() for ref in self.evidence_refs):
            raise ValueError("evidence_refs must contain non-empty strings")


@dataclass(frozen=True, slots=True)
class CuriosityDecision:
    """Inspectable ranking, including rejected candidates and score factors."""

    selected: CuriosityCandidate | None
    ranked: tuple[dict[str, object], ...]
    rejected: tuple[dict[str, str], ...]
    stability_pressure: float
    policy: str = "uncertainty_information_gain_v1"

    def to_dict(self) -> dict[str, object]:
        return {
            "policy": self.policy,
            "selected": asdict(self.selected) if self.selected else None,
            "ranked": [dict(item) for item in self.ranked],
            "rejected": [dict(item) for item in self.rejected],
            "stability_pressure": self.stability_pressure,
            "interpretation": (
                "Heuristic ranking of proposed knowledge gaps; not evidence "
                "of felt curiosity or subjective experience."
            ),
        }


class CuriositySelector:
    """Rank safe knowledge-gap proposals without requiring immediate reward.

    High stability pressure suppresses the contribution of exploration-related
    terms (information gain and novelty). Repeated questions are penalized.
    Candidates that exceed the risk limit or require external action are
    rejected by default.
    """

    def __init__(
        self,
        *,
        max_risk: float = 0.45,
        repetition_penalty: float = 0.12,
    ) -> None:
        self.max_risk = _unit_interval("max_risk", max_risk)
        self.repetition_penalty = _unit_interval(
            "repetition_penalty", repetition_penalty
        )

    @staticmethod
    def _question_key(candidate: CuriosityCandidate) -> tuple[str, str]:
        return (
            " ".join(candidate.gap_property.casefold().split()),
            " ".join(candidate.question.casefold().split()),
        )

    def _score(
        self,
        candidate: CuriosityCandidate,
        *,
        stability_pressure: float,
        repeated: bool,
    ) -> dict[str, float]:
        exploration_weight = 1.0 - 0.75 * stability_pressure
        terms = {
            "uncertainty": 0.20 * candidate.uncertainty,
            "information_gain": 0.25 * exploration_weight * candidate.expected_information_gain,
            "relevance": 0.20 * candidate.relevance,
            "novelty": 0.15 * exploration_weight * candidate.novelty,
            "cost_penalty": -0.10 * candidate.estimated_cost,
            "risk_penalty": -0.25 * candidate.risk,
            "repetition_penalty": -self.repetition_penalty if repeated else 0.0,
        }
        terms["exploration_weight"] = exploration_weight
        terms["total"] = sum(
            value for key, value in terms.items() if key != "exploration_weight"
        )
        return terms

    def rank(
        self,
        candidates: Iterable[CuriosityCandidate],
        *,
        stability_pressure: float = 0.0,
        prior_questions: Iterable[tuple[str, str]] = (),
    ) -> CuriosityDecision:
        """Rank explicit proposals; prior questions are (gap_property, question)."""
        stability = _unit_interval("stability_pressure", stability_pressure)
        proposals = list(candidates)
        if any(not isinstance(item, CuriosityCandidate) for item in proposals):
            raise ValueError("candidates must contain CuriosityCandidate values")
        ids = [item.candidate_id for item in proposals]
        if len(set(ids)) != len(ids):
            raise ValueError("candidate_id values must be unique")

        prior = {
            (" ".join(prop.casefold().split()), " ".join(question.casefold().split()))
            for prop, question in prior_questions
            if isinstance(prop, str) and prop.strip()
            and isinstance(question, str) and question.strip()
        }
        ranked: list[tuple[CuriosityCandidate, dict[str, float]]] = []
        rejected: list[dict[str, str]] = []
        for candidate in proposals:
            if candidate.risk > self.max_risk:
                rejected.append({
                    "candidate_id": candidate.candidate_id,
                    "reason": "risk_above_limit",
                })
                continue
            if candidate.requires_external_action:
                rejected.append({
                    "candidate_id": candidate.candidate_id,
                    "reason": "external_action_not_authorized",
                })
                continue
            repeated = self._question_key(candidate) in prior
            ranked.append((
                candidate,
                self._score(
                    candidate,
                    stability_pressure=stability,
                    repeated=repeated,
                ),
            ))

        ranked.sort(key=lambda item: (-item[1]["total"], item[0].candidate_id))
        alternatives = tuple(
            {"candidate": asdict(candidate), "score": score}
            for candidate, score in ranked
        )
        return CuriosityDecision(
            selected=ranked[0][0] if ranked else None,
            ranked=alternatives,
            rejected=tuple(rejected),
            stability_pressure=stability,
        )
