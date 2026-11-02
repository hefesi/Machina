"""Explicit, provenance-preserving perception input contract.

This boundary normalizes metadata without assuming a specific sensor, modality,
embedding model, or language model. The original payload remains available for
audit; normalized content is what downstream cognition receives.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from typing import Any, Mapping

from .contracts import now_utc


@dataclass(frozen=True, slots=True)
class NormalizedPerception:
    """A normalized observation with its original payload and transformation trace."""

    content: Any
    modality: str
    source: Mapping[str, Any]
    raw_payload: Any | None = None
    observed_at: str = field(default_factory=now_utc)
    confidence: float = 1.0
    raw_reference: str | None = None
    transformations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.modality, str) or not self.modality.strip():
            raise ValueError("modality must be a non-empty string")
        if not isinstance(self.source, Mapping):
            raise ValueError("source must be a mapping")
        if not isinstance(self.observed_at, str) or not self.observed_at.strip():
            raise ValueError("observed_at must be a non-empty timestamp string")
        if isinstance(self.confidence, bool) or not isinstance(self.confidence, (int, float)):
            raise ValueError("confidence must be a finite number between 0 and 1")
        if not math.isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be a finite number between 0 and 1")
        if self.raw_reference is not None and (
            not isinstance(self.raw_reference, str) or not self.raw_reference.strip()
        ):
            raise ValueError("raw_reference must be a non-empty string when provided")
        if isinstance(self.transformations, (str, bytes)):
            raise ValueError("transformations must be an iterable of non-empty strings")
        normalized_trace = tuple(self.transformations)
        if any(not isinstance(item, str) or not item.strip() for item in normalized_trace):
            raise ValueError("transformations must contain non-empty strings")
        object.__setattr__(self, "transformations", normalized_trace)
        for field_name, value in (
            ("content", self.content),
            ("raw_payload", self.raw_payload),
            ("source", dict(self.source)),
        ):
            try:
                json.dumps(value, ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field_name} must be JSON-serializable") from exc
        reliability = self.source.get("reliability", 1.0)
        if isinstance(reliability, bool) or not isinstance(reliability, (int, float)):
            raise ValueError("source reliability must be a finite number between 0 and 1")
        if not math.isfinite(reliability) or not 0.0 <= reliability <= 1.0:
            raise ValueError("source reliability must be a finite number between 0 and 1")

    @property
    def reliability(self) -> float:
        return float(self.source.get("reliability", 1.0))
