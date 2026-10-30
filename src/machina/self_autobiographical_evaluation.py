"""Evaluate outcomes associated with recalled autobiographical experiences.

The evaluator reports observed associations only. It does not infer that a
Self transformation caused an outcome, and it never changes goal priorities.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence

from .self_autobiographical_recall import SelfAutobiographicalMatch


@dataclass(frozen=True)
class SelfExperienceAssessment:
    transformation_event_id: str
    changed_paths: tuple[str, ...]
    experience_count: int
    successful_count: int
    unsuccessful_count: int
    neutral_count: int
    mean_outcome: float | None
    mean_absolute_prediction_error: float | None
    evidence_refs: tuple[str, ...]
    interpretation: str


@dataclass(frozen=True)
class SelfAutobiographicalEvaluation:
    assessments: tuple[SelfExperienceAssessment, ...]
    aggregate_experience_count: int
    limitations: tuple[str, ...]


class SelfAutobiographicalEvaluator:
    """Summarize explicit outcome labels in recalled, linked experience records."""

    @staticmethod
    def _number(value: object, field: str) -> float | None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        result = float(value)
        if not math.isfinite(result):
            raise ValueError(f"{field} must be finite")
        return result

    def evaluate(
        self, matches: Sequence[SelfAutobiographicalMatch]
    ) -> SelfAutobiographicalEvaluation:
        if isinstance(matches, (str, bytes)) or not isinstance(matches, Sequence):
            raise TypeError("matches must be a sequence")
        assessments = []
        total = 0
        for match in matches:
            if not isinstance(match, SelfAutobiographicalMatch):
                raise TypeError("matches must contain SelfAutobiographicalMatch values")
            outcomes: list[float] = []
            errors: list[float] = []
            successful = unsuccessful = neutral = 0
            evidence = set(match.evidence_refs)
            for experience in match.experience_records:
                content = experience.get("content", {})
                if not isinstance(content, dict):
                    continue
                outcome = self._number(content.get("actual_outcome"), "actual_outcome")
                expected = self._number(content.get("expected_outcome"), "expected_outcome")
                prediction_error = self._number(content.get("prediction_error"), "prediction_error")
                if outcome is None:
                    continue
                if not 0.0 <= outcome <= 1.0:
                    raise ValueError("actual_outcome must be within [0, 1]")
                outcomes.append(outcome)
                if expected is not None:
                    if not 0.0 <= expected <= 1.0:
                        raise ValueError("expected_outcome must be within [0, 1]")
                    errors.append(abs(outcome - expected))
                elif prediction_error is not None:
                    errors.append(abs(prediction_error))
                if outcome >= 0.7:
                    successful += 1
                elif outcome <= 0.3:
                    unsuccessful += 1
                else:
                    neutral += 1
                evidence.update(
                    ref for ref in experience.get("content", {}).get("evidence_refs", [])
                    if isinstance(ref, str) and ref
                )
            count = len(outcomes)
            total += count
            assessments.append(SelfExperienceAssessment(
                transformation_event_id=match.transformation_event_id,
                changed_paths=match.changed_paths,
                experience_count=count,
                successful_count=successful,
                unsuccessful_count=unsuccessful,
                neutral_count=neutral,
                mean_outcome=sum(outcomes) / count if count else None,
                mean_absolute_prediction_error=sum(errors) / len(errors) if errors else None,
                evidence_refs=tuple(sorted(evidence)),
                interpretation=(
                    "Observed outcomes are associated with explicitly linked episodes; "
                    "they do not establish that the transformation caused those outcomes."
                ),
            ))
        return SelfAutobiographicalEvaluation(
            assessments=tuple(assessments),
            aggregate_experience_count=total,
            limitations=(
                "Only explicit experience links are included.",
                "Missing outcome labels are not guessed.",
                "Association is not causation.",
                "Small samples are descriptive and should not be treated as reliable forecasts.",
            ),
        )
