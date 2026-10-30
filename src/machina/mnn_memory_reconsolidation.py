"""Evidence-gated proposals for version-safe memory reconsolidation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .fragment_memory import FragmentMemory, MemoryFragment


@dataclass(frozen=True, slots=True)
class MemoryRevisionProposal:
    """A side-effect-free revision tied to the exact content it reviewed."""

    fragment_id: str
    expected_content: str
    revised_content: str
    evidence_id: str
    confidence: float | None = None


class MNNMemoryReconsolidationPipeline:
    """Prepare and explicitly apply evidence-linked memory revisions.

    Proposal creation never mutates memory. Application uses compare-and-swap
    against the content observed at proposal time, preventing stale proposals
    from overwriting a newer revision.
    """

    def propose(
        self,
        memory: FragmentMemory,
        fragment_id: str,
        *,
        revised_content: str,
        evidence_id: str,
        confidence: float | None = None,
    ) -> MemoryRevisionProposal:
        if not isinstance(memory, FragmentMemory):
            raise TypeError("memory must be a FragmentMemory")
        for name, value in (("fragment_id", fragment_id), ("evidence_id", evidence_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if not isinstance(revised_content, str) or not revised_content.strip():
            raise ValueError("revised_content must be a non-empty string")
        if confidence is not None and (
            isinstance(confidence, bool) or not isinstance(confidence, (int, float))
            or not 0.0 <= float(confidence) <= 1.0
        ):
            raise ValueError("confidence must be between 0 and 1")
        current = memory.get(fragment_id, record_access=False)
        return MemoryRevisionProposal(
            fragment_id=fragment_id,
            expected_content=current.content,
            revised_content=revised_content.strip(),
            evidence_id=evidence_id,
            confidence=None if confidence is None else float(confidence),
        )

    def apply(
        self,
        memory: FragmentMemory,
        proposal: MemoryRevisionProposal,
        *,
        operation_id: str,
    ) -> tuple[MemoryFragment, dict[str, Any], bool]:
        if not isinstance(memory, FragmentMemory):
            raise TypeError("memory must be a FragmentMemory")
        if not isinstance(proposal, MemoryRevisionProposal):
            raise TypeError("proposal must be a MemoryRevisionProposal")
        if not isinstance(operation_id, str) or not operation_id.strip():
            raise ValueError("operation_id must be a non-empty string")
        return memory.reconsolidate(
            proposal.fragment_id,
            revised_content=proposal.revised_content,
            evidence_id=proposal.evidence_id,
            operation_id=operation_id,
            confidence=proposal.confidence,
            expected_content=proposal.expected_content,
        )
