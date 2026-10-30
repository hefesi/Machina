"""Evidence-gated learning from evaluated homeostatic interventions.

This learner estimates whether a named rule/direction tends to improve its
target. It only consumes explicit evaluator feedback and emits bounded gain
scales; it never changes rules or executes interventions.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from .homeostasis import HomeostaticProposal, HomeostaticRule


@dataclass(frozen=True)
class HomeostaticLearningEstimate:
    rule_name: str
    direction: str
    observations: int
    improvement_probability: float
    uncertainty: float
    recommended_gain_scale: float


class HomeostaticFeedbackLearner:
    """Beta-Bernoulli evaluator for explicitly assessed rule outcomes."""

    schema_version = 1

    def __init__(
        self,
        rules: Mapping[str, HomeostaticRule],
        *,
        prior_improvements: float = 1.0,
        prior_non_improvements: float = 1.0,
        min_gain_scale: float = 0.5,
        max_gain_scale: float = 1.5,
    ) -> None:
        if not isinstance(rules, Mapping) or not rules:
            raise ValueError("rules must be a non-empty mapping")
        if not all(isinstance(k, str) and k.strip() and isinstance(v, HomeostaticRule) for k, v in rules.items()):
            raise ValueError("rules must map names to HomeostaticRule values")
        for name, value in (("prior_improvements", prior_improvements), ("prior_non_improvements", prior_non_improvements)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if (isinstance(min_gain_scale, bool) or not isinstance(min_gain_scale, (int, float))
            or not math.isfinite(min_gain_scale) or min_gain_scale <= 0):
            raise ValueError("min_gain_scale must be finite and positive")
        if (isinstance(max_gain_scale, bool) or not isinstance(max_gain_scale, (int, float))
            or not math.isfinite(max_gain_scale) or max_gain_scale < min_gain_scale):
            raise ValueError("max_gain_scale must be finite and >= min_gain_scale")
        self.rules = dict(rules)
        self.prior_improvements = float(prior_improvements)
        self.prior_non_improvements = float(prior_non_improvements)
        self.min_gain_scale = float(min_gain_scale)
        self.max_gain_scale = float(max_gain_scale)
        self._counts = {
            (name, direction): {"improved": 0, "not_improved": 0}
            for name in self.rules for direction in ("below", "above")
        }
        self._observations: dict[str, dict[str, Any]] = {}

    def observe(
        self,
        rule_name: str,
        direction: str,
        *,
        improved: bool,
        evidence_ref: str,
        observation_id: str,
    ) -> HomeostaticLearningEstimate:
        """Record one explicit outcome; duplicate IDs are idempotent."""
        if rule_name not in self.rules:
            raise KeyError(f"unknown homeostatic rule: {rule_name}")
        if direction not in ("below", "above"):
            raise ValueError("direction must be 'below' or 'above'")
        if not isinstance(improved, bool):
            raise TypeError("improved must be bool")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise ValueError("evidence_ref must be non-empty")
        if not isinstance(observation_id, str) or not observation_id.strip():
            raise ValueError("observation_id must be non-empty")
        record = {"rule_name": rule_name, "direction": direction, "improved": improved, "evidence_ref": evidence_ref}
        existing = self._observations.get(observation_id)
        if existing is not None:
            if existing != record:
                raise ValueError("observation_id already exists with different feedback")
            return self.estimate(rule_name, direction)
        key = (rule_name, direction)
        bucket = "improved" if improved else "not_improved"
        self._counts[key][bucket] += 1
        self._observations[observation_id] = record
        return self.estimate(rule_name, direction)

    def estimate(self, rule_name: str, direction: str) -> HomeostaticLearningEstimate:
        if rule_name not in self.rules or direction not in ("below", "above"):
            raise ValueError("unknown rule or invalid direction")
        counts = self._counts[(rule_name, direction)]
        alpha = self.prior_improvements + counts["improved"]
        beta = self.prior_non_improvements + counts["not_improved"]
        total = alpha + beta
        probability = alpha / total
        variance = alpha * beta / (total * total * (total + 1))
        scale = self.min_gain_scale + probability * (self.max_gain_scale - self.min_gain_scale)
        return HomeostaticLearningEstimate(
            rule_name, direction, counts["improved"] + counts["not_improved"],
            probability, math.sqrt(variance), scale,
        )

    def adapt(self, proposal: HomeostaticProposal) -> HomeostaticProposal:
        """Return a scaled proposal using prior evaluated feedback only."""
        if not isinstance(proposal, HomeostaticProposal):
            raise TypeError("proposal must be a HomeostaticProposal")
        totals: dict[str, list[float]] = {}
        for name, deviation in proposal.deviations.items():
            rule = self.rules.get(name)
            if rule is None:
                continue
            direction = "below" if deviation < 0 else "above" if deviation > 0 else None
            if direction is None:
                continue
            estimate = self.estimate(name, direction)
            amount = proposal.adjustments.get(rule.drive)
            if amount is not None:
                totals.setdefault(rule.drive, []).append(estimate.recommended_gain_scale)
        adjustments = dict(proposal.adjustments)
        for drive, scales in totals.items():
            adjustments[drive] = max(-0.3, min(0.3, adjustments[drive] * (sum(scales) / len(scales))))
        rationale = proposal.rationale + ("homeostatic feedback scales derived from explicit prior evaluator outcomes",)
        return HomeostaticProposal(
            cycle_id=proposal.cycle_id,
            adjustments=adjustments,
            deviations=dict(proposal.deviations),
            persistence=dict(proposal.persistence),
            evidence_refs=proposal.evidence_refs,
            rationale=rationale,
        )

    def snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "rules": {name: {
                "metric_key": rule.metric_key, "drive": rule.drive,
                "lower": rule.lower, "upper": rule.upper,
                "below_adjustment": rule.below_adjustment,
                "above_adjustment": rule.above_adjustment,
            } for name, rule in self.rules.items()},
            "prior_improvements": self.prior_improvements,
            "prior_non_improvements": self.prior_non_improvements,
            "min_gain_scale": self.min_gain_scale,
            "max_gain_scale": self.max_gain_scale,
            "observations": dict(self._observations),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping[str, Any]) -> "HomeostaticFeedbackLearner":
        if not isinstance(data, Mapping) or data.get("schema_version") != cls.schema_version:
            raise ValueError("unsupported HomeostaticFeedbackLearner snapshot")
        raw_rules = data.get("rules")
        raw_observations = data.get("observations")
        if not isinstance(raw_rules, Mapping) or not isinstance(raw_observations, Mapping):
            raise ValueError("malformed learner snapshot")
        rules = {name: HomeostaticRule(**rule) for name, rule in raw_rules.items()}
        learner = cls(
            rules,
            prior_improvements=data.get("prior_improvements"),
            prior_non_improvements=data.get("prior_non_improvements"),
            min_gain_scale=data.get("min_gain_scale"),
            max_gain_scale=data.get("max_gain_scale"),
        )
        for observation_id, record in raw_observations.items():
            if not isinstance(observation_id, str) or not isinstance(record, Mapping):
                raise ValueError("malformed feedback observation")
            estimate_before = learner.estimate(record.get("rule_name"), record.get("direction"))
            del estimate_before
            learner.observe(
                record.get("rule_name"), record.get("direction"),
                improved=record.get("improved"),
                evidence_ref=record.get("evidence_ref"),
                observation_id=observation_id,
            )
        return learner
