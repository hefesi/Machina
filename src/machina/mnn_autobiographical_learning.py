"""Evidence-bounded learning guidance from autobiographical outcome summaries.

The advisor turns explicit, linked outcome observations into review signals.
It does not mutate memory, the Self-model, goals, or neural weights.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from .self_autobiographical_evaluation import SelfAutobiographicalEvaluation


@dataclass(frozen=True, slots=True)
class AutobiographicalLearningSignal:
    transformation_event_id: str
    changed_paths: tuple[str, ...]
    observation_count: int
    mean_outcome: float | None
    mean_absolute_prediction_error: float | None
    evidence_refs: tuple[str, ...]
    recommendation: str
    rationale: str


class MNNAutobiographicalLearningAdvisor:
    """Classify autobiographical evidence for explicit human/system review."""

    def __init__(
        self,
        *,
        minimum_observations: int = 3,
        positive_outcome_threshold: float = 0.7,
        negative_outcome_threshold: float = 0.3,
        acceptable_prediction_error: float = 0.2,
    ) -> None:
        if isinstance(minimum_observations, bool) or not isinstance(minimum_observations, int) or minimum_observations < 1:
            raise ValueError("minimum_observations must be a positive integer")
        for name, value in (
            ("positive_outcome_threshold", positive_outcome_threshold),
            ("negative_outcome_threshold", negative_outcome_threshold),
            ("acceptable_prediction_error", acceptable_prediction_error),
        ):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be finite and within [0, 1]")
        if negative_outcome_threshold >= positive_outcome_threshold:
            raise ValueError("negative threshold must be lower than positive threshold")
        self.minimum_observations = minimum_observations
        self.positive_outcome_threshold = float(positive_outcome_threshold)
        self.negative_outcome_threshold = float(negative_outcome_threshold)
        self.acceptable_prediction_error = float(acceptable_prediction_error)

    def advise(self, evaluation: SelfAutobiographicalEvaluation) -> tuple[AutobiographicalLearningSignal, ...]:
        if not isinstance(evaluation, SelfAutobiographicalEvaluation):
            raise TypeError("evaluation must be a SelfAutobiographicalEvaluation")
        signals = []
        for item in evaluation.assessments:
            if item.experience_count < self.minimum_observations or item.mean_outcome is None:
                recommendation = "insufficient_evidence"
                rationale = "Too few explicitly labeled outcomes for a stable review signal."
            elif item.mean_outcome <= self.negative_outcome_threshold:
                recommendation = "review_or_revise"
                rationale = "Observed outcomes trend negative; inspect context and alternative explanations."
            elif item.mean_outcome >= self.positive_outcome_threshold:
                if (
                    item.mean_absolute_prediction_error is not None
                    and item.mean_absolute_prediction_error <= self.acceptable_prediction_error
                ):
                    recommendation = "candidate_for_reinforcement"
                    rationale = "Observed outcomes trend positive and recorded predictions were reasonably calibrated."
                else:
                    recommendation = "monitor_calibration"
                    rationale = "Outcomes trend positive, but prediction calibration is missing or outside the configured bound."
            else:
                recommendation = "continue_observation"
                rationale = "Observed outcomes are mixed or intermediate; no directional update is advised."
            signals.append(AutobiographicalLearningSignal(
                transformation_event_id=item.transformation_event_id,
                changed_paths=item.changed_paths,
                observation_count=item.experience_count,
                mean_outcome=item.mean_outcome,
                mean_absolute_prediction_error=item.mean_absolute_prediction_error,
                evidence_refs=item.evidence_refs,
                recommendation=recommendation,
                rationale=rationale,
            ))
        return tuple(signals)
