"""Record auditable MNN telemetry as operational SelfModel observations.

This is a one-way observation bridge. It records measured runtime state but
does not claim that activations reveal thoughts, feelings, or consciousness.
"""
from __future__ import annotations

import math
from typing import Any

from .mnn_organism import OrganismStep
from .self_model import SelfModel


class MNNStateSelfObserver:
    """Reflect an executed MNNOrganism step into evidence-backed SelfModel beliefs."""

    def __init__(self, self_model: SelfModel) -> None:
        if not isinstance(self_model, SelfModel):
            raise TypeError("self_model must be a SelfModel")
        self.self_model = self_model

    def observe(
        self,
        step: OrganismStep,
        *,
        cycle_id: str,
        evidence_ref: str,
    ) -> dict[str, Any]:
        """Record exact telemetry from one completed organism step."""
        if not isinstance(step, OrganismStep):
            raise TypeError("step must be an OrganismStep")
        if not isinstance(cycle_id, str) or not cycle_id.strip():
            raise ValueError("cycle_id must be a non-empty string")
        if not isinstance(evidence_ref, str) or not evidence_ref.strip():
            raise ValueError("evidence_ref must be a non-empty string")
        observations: dict[str, Any] = {}
        refs: dict[str, str] = {}
        statuses: dict[str, str] = {}
        confidences: dict[str, float] = {}

        def add(name: str, value: float) -> None:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError(f"telemetry {name!r} must be finite")
            key = f"internal.mnn.{name}"
            observations[key] = float(value)
            refs[key] = evidence_ref
            statuses[key] = "observed"
            confidences[key] = 1.0

        if isinstance(step.timestep, bool) or not isinstance(step.timestep, int) or step.timestep < 1:
            raise ValueError("step timestep must be a positive integer")
        add("timestep", step.timestep)
        add("prediction_error", step.prediction_error)
        add("exploration_drive", step.exploration_drive)
        add("plasticity_gain", step.plasticity_gain)
        add("attention_gain", step.attention_gain)
        for unit_id, activation in step.neural_state.items():
            if not isinstance(unit_id, str) or not unit_id.strip():
                raise ValueError("neural unit IDs must be non-empty strings")
            add(f"activation.{unit_id}", activation)
        for name, concentration in step.chemical_state.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("chemical signal names must be non-empty strings")
            add(f"chemical.{name}", concentration)
        for name, urgency in step.motivation_urgencies.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError("motivation drive names must be non-empty strings")
            add(f"motivation.{name}", urgency)

        return self.self_model.update(
            observations,
            cycle_id=cycle_id,
            evidence_refs=refs,
            statuses=statuses,
            confidences=confidences,
        )
