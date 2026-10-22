"""D08.3: auditable computational relevance, explicitly not a feeling model."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelevanceWeights:
    goal_alignment: float = 0.4
    novelty: float = 0.2
    future_decision_impact: float = 0.25
    urgency: float = 0.15

    def __post_init__(self) -> None:
        values = (
            self.goal_alignment,
            self.novelty,
            self.future_decision_impact,
            self.urgency,
        )
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in values):
            raise ValueError("weights must be between 0 and 1")
        if sum(values) == 0:
            raise ValueError("at least one relevance weight must be positive")


@dataclass(frozen=True)
class EventSignals:
    goal_alignment: float
    novelty: float
    future_decision_impact: float
    urgency: float

    def __post_init__(self) -> None:
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1 for value in (
            self.goal_alignment, self.novelty, self.future_decision_impact, self.urgency
        )):
            raise ValueError("event signals must be between 0 and 1")


def score_relevance(signals: EventSignals, weights: RelevanceWeights = RelevanceWeights()) -> float:
    """Return a normalized weighted score of operational significance.

    This score represents decision/memory relevance, never pleasure, pain,
    emotion, or phenomenal consciousness.
    """
    values = (
        (signals.goal_alignment, weights.goal_alignment),
        (signals.novelty, weights.novelty),
        (signals.future_decision_impact, weights.future_decision_impact),
        (signals.urgency, weights.urgency),
    )
    denominator = sum(weight for _, weight in values)
    return sum(signal * weight for signal, weight in values) / denominator
