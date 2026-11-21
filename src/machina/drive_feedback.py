"""Shared validation and aggregation for bounded drive feedback.

The same contract is consumed by curiosity ranking and final autonomy scoring,
so neither layer can silently diverge on accepted feedback values.
"""
from __future__ import annotations

import math
from typing import Mapping


def merge_drive_adjustments(*sources: Mapping[str, float]) -> dict[str, float]:
    """Merge bounded feedback sources deterministically, then clamp once.

    Each provider must contribute within [-0.3, 0.3]. Contributions for the
    same drive are summed with stable ordering and math.fsum before the shared
    result bound is applied.
    """
    contributions: dict[str, list[float]] = {}
    for source in sources:
        if not isinstance(source, Mapping):
            raise ValueError("drive adjustment sources must be mappings")
        for drive, raw_value in source.items():
            if not isinstance(drive, str) or not drive.strip():
                raise ValueError("drive adjustment names must be non-empty strings")
            if (
                isinstance(raw_value, bool)
                or not isinstance(raw_value, (int, float))
                or not math.isfinite(raw_value)
            ):
                raise ValueError(f"drive adjustment for {drive} must be a finite number")
            if not -0.3 <= raw_value <= 0.3:
                raise ValueError("each drive adjustment must be within [-0.3, 0.3]")
            contributions.setdefault(drive, []).append(float(raw_value))
    return {
        drive: max(-0.3, min(0.3, math.fsum(sorted(values))))
        for drive, values in sorted(contributions.items())
    }
