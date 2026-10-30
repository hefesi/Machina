"""Explicit, bounded proposals for internal operational self-regulation.

The regulator reads measured MNN telemetry and proposes goal-selection biases.
It never mutates motivation, neural weights, SelfModel, or executes actions.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .self_model import SelfModel


@dataclass(frozen=True)
class RegulationProposal:
    cycle_id: str
    adjustments: Mapping[str, float]
    metric_errors: Mapping[str, float]
    rationale: tuple[str, ...]
    evidence_refs: tuple[str, ...]


class SelfRegulationController:
    """Translate explicit telemetry targets into bounded autonomy adjustments."""

    _METRICS = {
        "prediction_error": "internal.mnn.prediction_error",
        "exploration_drive": "internal.mnn.exploration_drive",
        "attention_gain": "internal.mnn.attention_gain",
    }

    def __init__(
        self,
        self_model: SelfModel,
        drive_mapping: Mapping[str, str],
        *,
        targets: Mapping[str, float] | None = None,
        gain: float = 0.15,
        max_adjustment: float = 0.15,
    ) -> None:
        if not isinstance(self_model, SelfModel):
            raise TypeError("self_model must be a SelfModel")
        if not isinstance(drive_mapping, Mapping) or not drive_mapping:
            raise ValueError("drive_mapping must be a non-empty mapping")
        mapping = dict(drive_mapping)
        if any(not isinstance(metric, str) or metric not in self._METRICS
               or not isinstance(drive, str) or not drive.strip()
               for metric, drive in mapping.items()):
            raise ValueError("drive_mapping must map supported metrics to drive names")
        self.targets = dict(targets or {
            "prediction_error": 0.0,
            "exploration_drive": 0.5,
            "attention_gain": 0.5,
        })
        if set(self.targets) != set(mapping):
            raise ValueError("targets and drive_mapping must contain the same metric keys")
        for name, target in self.targets.items():
            self._unit_interval(name, target)
        self._unit_interval("gain", gain)
        self._unit_interval("max_adjustment", max_adjustment)
        if gain > 0.3 or max_adjustment > 0.3:
            raise ValueError("gain and max_adjustment must not exceed 0.3")
        self.self_model = self_model
        self.drive_mapping = mapping
        self.gain = float(gain)
        self.max_adjustment = float(max_adjustment)

    @staticmethod
    def _unit_interval(name: str, value: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be finite and within [0, 1]")
        return float(value)

    def propose(self, *, cycle_id: str | None = None) -> RegulationProposal:
        """Create an auditable proposal from the latest observed telemetry."""
        beliefs = self.self_model.beliefs
        selected_cycle = cycle_id or self.self_model.cycle_id
        if not isinstance(selected_cycle, str) or not selected_cycle.strip():
            raise ValueError("SelfModel has no cycle; supply cycle_id")
        adjustments: dict[str, float] = {}
        errors: dict[str, float] = {}
        evidence: set[str] = set()
        rationale: list[str] = []
        for metric, drive in self.drive_mapping.items():
            key = self._METRICS[metric]
            belief = beliefs.get(key)
            if not belief or belief.get("status") != "observed" or belief.get("value") is None:
                continue
            value = belief["value"]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                continue
            target = self.targets[metric]
            # Error is signed: a high value raises the corresponding drive's
            # selection bias; a low value lowers it. For prediction error,
            # high error increases the bias toward the mapped corrective drive.
            error = float(value) - target
            errors[metric] = error
            adjustment = max(-self.max_adjustment, min(
                self.max_adjustment, error * self.gain
            ))
            adjustments[drive] = adjustment
            ref = belief.get("evidence_ref")
            if isinstance(ref, str) and ref:
                evidence.add(ref)
            rationale.append(
                f"{metric}: observed={float(value):.6f}, target={target:.6f}, "
                f"drive={drive}, adjustment={adjustment:.6f}"
            )
        return RegulationProposal(
            cycle_id=selected_cycle,
            adjustments=adjustments,
            metric_errors=errors,
            rationale=tuple(rationale),
            evidence_refs=tuple(sorted(evidence)),
        )
