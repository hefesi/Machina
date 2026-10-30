"""Translate analyzed Self history into bounded, auditable decision feedback.

The adapter is deliberately policy-driven: the caller maps transition statuses
to drive adjustments. Historical records are evidence for a proposal, not
automatic proof of capability, preference, or subjective identity.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from .self_state_dynamics import SelfStateTransition


@dataclass(frozen=True)
class SelfHistoryRule:
    property_name: str
    status_adjustments: Mapping[str, Mapping[str, float]]


@dataclass(frozen=True)
class SelfHistoryInfluence:
    adjustments: Mapping[str, float]
    transitions: tuple[SelfStateTransition, ...]
    evidence_refs: tuple[str, ...]
    rationale: tuple[str, ...]


class SelfHistoryInfluenceAdapter:
    """Create bounded drive biases from explicitly configured history rules."""

    _STATUSES = {"stable", "persistent_since_change", "recurrent", "reverted", "changed"}

    def __init__(
        self,
        rules: Sequence[SelfHistoryRule],
        *,
        max_adjustment: float = 0.3,
    ) -> None:
        if isinstance(rules, (str, bytes)) or not isinstance(rules, Sequence) or not rules:
            raise ValueError("rules must be a non-empty sequence")
        if (isinstance(max_adjustment, bool) or not isinstance(max_adjustment, (int, float))
            or not math.isfinite(max_adjustment) or not 0 < max_adjustment <= 0.3):
            raise ValueError("max_adjustment must be finite and in (0, 0.3]")
        normalized: dict[str, SelfHistoryRule] = {}
        for rule in rules:
            if not isinstance(rule, SelfHistoryRule):
                raise TypeError("rules must contain SelfHistoryRule values")
            if not isinstance(rule.property_name, str) or not rule.property_name.strip():
                raise ValueError("property_name must be non-empty")
            if rule.property_name in normalized:
                raise ValueError(f"duplicate rule for {rule.property_name}")
            if not isinstance(rule.status_adjustments, Mapping):
                raise ValueError("status_adjustments must be a mapping")
            for status, adjustments in rule.status_adjustments.items():
                if status not in self._STATUSES or not isinstance(adjustments, Mapping):
                    raise ValueError("invalid status adjustment mapping")
                for drive, amount in adjustments.items():
                    if not isinstance(drive, str) or not drive.strip():
                        raise ValueError("drive names must be non-empty")
                    if (isinstance(amount, bool) or not isinstance(amount, (int, float))
                        or not math.isfinite(amount) or not -max_adjustment <= amount <= max_adjustment):
                        raise ValueError("adjustments must be finite and within configured bounds")
            normalized[rule.property_name] = rule
        self.rules = normalized
        self.max_adjustment = float(max_adjustment)

    def prepare(
        self,
        transitions: Sequence[SelfStateTransition],
    ) -> SelfHistoryInfluence:
        if isinstance(transitions, (str, bytes)) or not isinstance(transitions, Sequence):
            raise TypeError("transitions must be a sequence")
        adjustments: dict[str, float] = {}
        selected: list[SelfStateTransition] = []
        evidence: set[str] = set()
        rationale: list[str] = []
        for transition in transitions:
            if not isinstance(transition, SelfStateTransition):
                raise TypeError("transitions must contain SelfStateTransition values")
            rule = self.rules.get(transition.property_name)
            if rule is None:
                continue
            status_adjustments = rule.status_adjustments.get(transition.status, {})
            selected.append(transition)
            evidence.update(ref for ref in transition.evidence_refs if isinstance(ref, str) and ref)
            for drive, amount in status_adjustments.items():
                adjustments[drive] = max(
                    -self.max_adjustment,
                    min(self.max_adjustment, adjustments.get(drive, 0.0) + float(amount)),
                )
            rationale.append(
                f"{transition.property_name}: history status={transition.status}; "
                f"observations={transition.observations}; configured drives={sorted(status_adjustments)}"
            )
        return SelfHistoryInfluence(
            adjustments=adjustments,
            transitions=tuple(selected),
            evidence_refs=tuple(sorted(evidence)),
            rationale=tuple(rationale),
        )
