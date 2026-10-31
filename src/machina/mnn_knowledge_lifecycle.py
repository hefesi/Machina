"""MNN knowledge lifecycle: evidence discovery, refresh, and audit."""
from __future__ import annotations
from dataclasses import dataclass
from .fragment_memory import FragmentMemory, MemoryFragment
from .mnn_concept_review import ConceptReview, MNNConceptReviewer
from .mnn_concepts import ConceptHypothesis, MNNConceptBuilder

@dataclass(frozen=True, slots=True)
class MNNKnowledgeLifecycleResult:
    """Immutable summary of one maintenance cycle."""
    hypotheses: tuple[ConceptHypothesis, ...]
    materialized_concepts: tuple[MemoryFragment, ...]
    reviews_before_refresh: tuple[ConceptReview, ...]
    reviews_after_refresh: tuple[ConceptReview, ...]
    audit_fragments: tuple[MemoryFragment, ...]

    @property
    def conflicted_count(self) -> int:
        return sum(item.state == "conflicted" for item in self.reviews_after_refresh)

    @property
    def stale_count(self) -> int:
        return sum(item.state == "stale" for item in self.reviews_after_refresh)

    @property
    def unverified_count(self) -> int:
        return sum(item.state == "unverified" for item in self.reviews_after_refresh)

class MNNKnowledgeLifecycle:
    """Coordinate transparent, non-destructive concept maintenance.

    Discovery is tag-based and relations are explicitly supplied; this class
    does not claim semantic understanding or infer relations from prose.
    """
    schema_version = 1

    def __init__(self, memory: FragmentMemory, *, min_support: int = 2) -> None:
        if not isinstance(memory, FragmentMemory):
            raise TypeError("memory must be a FragmentMemory")
        self.memory = memory
        self.builder = MNNConceptBuilder(memory, min_support=min_support)
        self.reviewer = MNNConceptReviewer(memory, min_support=min_support)

    def run(self, *, refresh: bool = True, persist_audit: bool = True) -> MNNKnowledgeLifecycleResult:
        """Run one pass; source fragments and old concept snapshots are never rewritten."""
        if not isinstance(refresh, bool):
            raise ValueError("refresh must be boolean")
        if not isinstance(persist_audit, bool):
            raise ValueError("persist_audit must be boolean")
        before = tuple(self.reviewer.review())
        hypotheses = tuple(self.builder.discover())
        materialized = tuple(self.builder.materialize(item) for item in hypotheses) if refresh else ()
        after = tuple(self.reviewer.review()) if refresh else before
        audit = tuple(self.reviewer.persist_review_log()) if persist_audit else ()
        return MNNKnowledgeLifecycleResult(hypotheses, materialized, before, after, audit)
