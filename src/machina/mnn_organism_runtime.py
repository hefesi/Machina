"""Explicit composition of the MNN organism with VirtualBrain adapters.

The factory prevents accidental split-brain wiring: cognition and agency must
share one organism instance, including its motivational and memory state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .components import AgencyPolicy, CognitionEngine
from .mnn_organism import MNNOrganism
from .mnn_organism_adapter import MNNOrganismCognitionAdapter
from .mnn_organism_agency import MNNOrganismAgencyAdapter


@dataclass(frozen=True, slots=True)
class MNNOrganismRuntime:
    """A coherent adapter pair over one persistent MNNOrganism instance."""

    organism: MNNOrganism
    cognition: MNNOrganismCognitionAdapter
    agency: MNNOrganismAgencyAdapter

    def __post_init__(self) -> None:
        if self.cognition.organism is not self.organism:
            raise ValueError("cognition adapter must share the runtime organism")
        if self.agency.organism is not self.organism:
            raise ValueError("agency adapter must share the runtime organism")

    @property
    def motivation(self) -> Any | None:
        """Return the organism's MotivationSystem for run_deliberated_cycle()."""
        return self.organism.motivation

    def drive_adjustments(self, *, gain: float = 0.3) -> dict[str, float]:
        """Return bounded temporal drive adjustments for goal deliberation."""
        motivation = self.organism.motivation
        if motivation is None:
            return {}
        return motivation.autonomy_adjustments(gain=gain)

    def run_deliberated_cycle(
        self,
        brain: Any,
        observation: Any,
        context: Any,
        **cycle_kwargs: Any,
    ) -> Any:
        """Run one VirtualBrain cycle using this runtime's shared MNN state.

        The brain must have been constructed with this runtime's exact
        cognition and agency adapters, preventing split-organism wiring.
        """
        if getattr(brain, "cognition", None) is not self.cognition:
            raise ValueError("brain cognition must be this runtime's cognition adapter")
        if getattr(brain, "agency", None) is not self.agency:
            raise ValueError("brain agency must be this runtime's agency adapter")
        if "motivation" in cycle_kwargs or "drive_adjustments" in cycle_kwargs:
            raise TypeError("motivation and drive_adjustments are supplied by the runtime")
        return brain.run_deliberated_cycle(
            observation,
            context,
            motivation=self.motivation,
            drive_adjustments=self.drive_adjustments(),
            **cycle_kwargs,
        )

    def ranked_drives(self) -> list[tuple[str, float]]:
        """Expose current motivational urgency without mutating organism state."""
        motivation = self.organism.motivation
        if motivation is None:
            return []
        return motivation.ranked_drives()


def build_mnn_organism_runtime(
    organism: MNNOrganism,
    *,
    input_features: Mapping[str, str],
    target_unit: str,
    cognition: CognitionEngine | None = None,
    agency: AgencyPolicy | None = None,
    outcome_learning_rate: float = 0.01,
    memory_weight: float = 0.25,
    memory_limit: int = 5,
) -> MNNOrganismRuntime:
    """Build cognition and agency adapters sharing exactly one organism.

    The returned runtime can be wired explicitly into VirtualBrain:
        brain = VirtualBrain(..., cognition=runtime.cognition,
                             agency=runtime.agency,
                             internal_deliberator=...)
    Its motivation and drive adjustments can be passed to
    run_deliberated_cycle(). The factory does not create databases, execute
    actions, or silently enable external capabilities.
    """
    if not isinstance(organism, MNNOrganism):
        raise TypeError("organism must be an MNNOrganism")
    cognition_adapter = MNNOrganismCognitionAdapter(
        organism,
        input_features=input_features,
        base_engine=cognition,
        outcome_learning_rate=outcome_learning_rate,
    )
    agency_adapter = MNNOrganismAgencyAdapter(
        organism,
        target_unit=target_unit,
        base_policy=agency,
        memory_weight=memory_weight,
        limit=memory_limit,
    )
    return MNNOrganismRuntime(
        organism=organism,
        cognition=cognition_adapter,
        agency=agency_adapter,
    )
