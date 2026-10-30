"""Translate autobiographical Self-change records into explicit MNN inputs.

This adapter is opt-in: callers map SelfModel paths to neural units and decide
when to pass the resulting signals to MNNOrganism.step. It does not infer
meaning from arbitrary model values or execute a neural transition.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping

from .self_experience_integration import SelfExperienceIntegrator


@dataclass(frozen=True)
class SelfInfluence:
    """Auditable neural input proposal derived from recorded Self changes."""

    neural_inputs: Mapping[str, float]
    evidence_by_unit: Mapping[str, tuple[str, ...]]
    paths_by_unit: Mapping[str, tuple[str, ...]]
    transformation_event_ids: tuple[str, ...]


class SelfInfluenceAdapter:
    """Create bounded, caller-mapped neural signals from autobiographical changes."""

    _STATUS_SIGNAL = {
        "observed_once": 0.25,
        "reinforced": 0.5,
        "reversed": -0.5,
    }

    def __init__(
        self,
        integrator: SelfExperienceIntegrator,
        path_to_unit: Mapping[str, str],
        *,
        gain: float = 1.0,
    ) -> None:
        if not isinstance(integrator, SelfExperienceIntegrator):
            raise TypeError("integrator must be a SelfExperienceIntegrator")
        if not isinstance(path_to_unit, Mapping) or not path_to_unit:
            raise ValueError("path_to_unit must be a non-empty mapping")
        normalized = dict(path_to_unit)
        if any(
            not isinstance(path, str) or not path.strip()
            or not isinstance(unit, str) or not unit.strip()
            for path, unit in normalized.items()
        ):
            raise ValueError("path_to_unit must map non-empty paths to unit IDs")
        if isinstance(gain, bool) or not isinstance(gain, (int, float)) or not math.isfinite(gain) or not 0.0 <= gain <= 2.0:
            raise ValueError("gain must be finite and within [0, 2]")
        self.integrator = integrator
        self.path_to_unit = normalized
        self.gain = float(gain)

    def prepare(self) -> SelfInfluence:
        """Aggregate mapped change statuses into bounded signed unit inputs."""
        totals: dict[str, list[float]] = {}
        evidence: dict[str, set[str]] = {}
        paths: dict[str, set[str]] = {}
        event_ids: set[str] = set()
        projection = self.integrator.integrate()
        for transformation in projection["transformations"]:
            event_id = transformation["event_id"]
            for path, unit in self.path_to_unit.items():
                status = transformation["durability"].get(path, {}).get("status")
                if status not in self._STATUS_SIGNAL:
                    continue
                totals.setdefault(unit, []).append(self._STATUS_SIGNAL[status] * self.gain)
                paths.setdefault(unit, set()).add(path)
                evidence.setdefault(unit, set()).update(transformation["evidence_refs"])
                event_ids.add(event_id)
        signals = {
            unit: max(-1.0, min(1.0, sum(values) / len(values)))
            for unit, values in totals.items()
        }
        return SelfInfluence(
            neural_inputs=signals,
            evidence_by_unit={
                unit: tuple(sorted(refs)) for unit, refs in evidence.items()
            },
            paths_by_unit={
                unit: tuple(sorted(items)) for unit, items in paths.items()
            },
            transformation_event_ids=tuple(sorted(event_ids)),
        )
