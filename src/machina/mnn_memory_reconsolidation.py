"""Evidence-gated proposals for version-safe memory reconsolidation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .fragment_memory import FragmentMemory, MemoryFragment


@dataclass(frozen=True, slots=True)
class MemoryRevisionProposal:
    """A side-effect-free revision tied to the exact content it reviewed."""

    fragment_id: str
    expected_content: str
    revised_content: str
    evidence_id: str
    confidence: float | None = None
    context_refs: tuple[str, ...] = ()


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
        context_refs: Iterable[str] = (),
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
        raw_refs = tuple(context_refs)
        if not all(isinstance(ref, str) and ref.strip() for ref in raw_refs):
            raise ValueError("context_refs must contain non-empty strings")
        normalized_refs = tuple(sorted(set(raw_refs)))
        current = memory.get(fragment_id, record_access=False)
        return MemoryRevisionProposal(
            fragment_id=fragment_id,
            expected_content=current.content,
            revised_content=revised_content.strip(),
            evidence_id=evidence_id,
            confidence=None if confidence is None else float(confidence),
            context_refs=normalized_refs,
        )


    def propose_from_autobiographical_context(
        self,
        memory: FragmentMemory,
        fragment_id: str,
        *,
        revised_content: str,
        evidence_id: str,
        autobiographical_matches: Iterable[Any],
        confidence: float | None = None,
    ) -> MemoryRevisionProposal:
        """Create a proposal grounded in explicitly returned autobiographical refs.

        This method only attaches provenance. It does not treat lexical recall,
        a remembered episode, or a self-reported outcome as proof that the
        proposed content is true.
        """
        matches = tuple(autobiographical_matches)
        if not matches:
            raise ValueError("autobiographical_matches must not be empty")
        refs: set[str] = set()
        for match in matches:
            refs.update(
                ref for ref in getattr(match, "evidence_refs", ())
                if isinstance(ref, str) and ref.strip()
            )
            for record in getattr(match, "experience_records", ()):
                event_id = record.get("event_id") if isinstance(record, dict) else None
                if isinstance(event_id, str) and event_id.strip():
                    refs.add(event_id)
        if evidence_id not in refs:
            raise ValueError(
                "evidence_id must match an explicit evidence or linked experience reference"
            )
        return self.propose(
            memory, fragment_id, revised_content=revised_content,
            evidence_id=evidence_id, confidence=confidence,
            context_refs=refs,
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
