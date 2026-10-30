"""Revision checks for persisted concepts as new evidence arrives.

The reviewer compares immutable concept snapshots with current hypotheses. It
never rewrites source fragments or old concepts; stale/current/conflicted state
is a derived view that can be recomputed at any time.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Literal

from .fragment_memory import FragmentMemory, MemoryFragment
from .mnn_concepts import ConceptHypothesis, MNNConceptBuilder
from .mnn_concept_relations import MNNConceptRelationStore

RevisionState = Literal["current", "conflicted", "stale", "unverified"]


@dataclass(frozen=True, slots=True)
class ConceptReview:
    concept: MemoryFragment
    state: RevisionState
    current_evidence_ids: tuple[str, ...]
    added_evidence_ids: tuple[str, ...]
    missing_evidence_ids: tuple[str, ...]
    current_status: str | None
    explanation: str
    explicit_relation_ids: tuple[str, ...] = ()
    related_concept_ids: tuple[str, ...] = ()
    relation_evidence_ids: tuple[str, ...] = ()


class MNNConceptReviewer:
    """Check whether persisted concept snapshots still match current evidence."""

    schema_version = 1

    def __init__(self, memory: FragmentMemory, *, min_support: int = 2) -> None:
        self.memory = memory
        self.builder = MNNConceptBuilder(memory, min_support=min_support)
        self.relations = MNNConceptRelationStore(memory)

    def review(self) -> list[ConceptReview]:
        """Return review state for every stored concept without mutating records."""
        current_by_key: dict[str, ConceptHypothesis] = {
            item.key: item for item in self.builder.discover()
        }
        reviews: list[ConceptReview] = []
        for concept in self.memory.archive():
            if concept.kind != "concept":
                continue
            key = concept.metadata.get("concept_key")
            recorded_ids = concept.metadata.get("evidence_ids")
            if not isinstance(key, str) or not isinstance(recorded_ids, list) or not all(isinstance(item, str) for item in recorded_ids):
                reviews.append(ConceptReview(
                    concept, "unverified", (), (), (), None,
                    "Concept lacks valid provenance metadata; it was not classified as current.",
                ))
                continue
            hypothesis = current_by_key.get(key)
            if hypothesis is None:
                reviews.append(ConceptReview(
                    concept, "stale", (), (), tuple(recorded_ids), None,
                    "No current hypothesis meets the discovery threshold for this concept key.",
                ))
                continue
            previous = set(recorded_ids)
            current = set(hypothesis.evidence_ids)
            added = tuple(sorted(current - previous))
            missing = tuple(sorted(previous - current))
            explicit_relations = self.relations.for_concept(concept.id)
            contradictions = tuple(
                relation for relation in explicit_relations
                if relation.relationship == "contradicts"
            )
            relation_ids = tuple(sorted(relation.relation_id for relation in contradictions))
            related_ids = tuple(sorted({
                relation.target_concept_id if relation.source_concept_id == concept.id
                else relation.source_concept_id
                for relation in contradictions
            }))
            relation_evidence = tuple(sorted({
                evidence_id for relation in contradictions
                for evidence_id in relation.evidence_ids
            }))
            if hypothesis.status == "conflicted" or contradictions:
                state: RevisionState = "conflicted"
                explanation = "Current evidence or an explicit persisted concept relation records a contradiction."
            elif added or missing:
                state = "stale"
                explanation = "The evidence set changed; this concept is an older snapshot and should be refreshed before use."
            else:
                state = "current"
                explanation = "The recorded evidence IDs match the current hypothesis and no explicit conflict is present."
            reviews.append(ConceptReview(
                concept=concept,
                state=state,
                current_evidence_ids=tuple(sorted(current)),
                added_evidence_ids=added,
                missing_evidence_ids=missing,
                current_status=hypothesis.status,
                explanation=explanation,
                explicit_relation_ids=relation_ids,
                related_concept_ids=related_ids,
                relation_evidence_ids=relation_evidence,
            ))
        reviews.sort(key=lambda item: (item.state, item.concept.id))
        return reviews

    def refresh(self) -> list[MemoryFragment]:
        """Materialize current hypotheses; prior concept snapshots remain archived."""
        return self.builder.consolidate()

    def persist_review_log(self) -> list[MemoryFragment]:
        """Persist idempotent audit fragments for the current review states.

        A new log fragment is created only when the reviewed state or evidence
        snapshot changes. The log itself is not used as concept evidence.
        """
        logs: list[MemoryFragment] = []
        for review in self.review():
            recorded = review.concept.metadata.get("evidence_ids", [])
            if not isinstance(recorded, list) or not all(isinstance(item, str) for item in recorded):
                recorded = []
            evidence = review.current_evidence_ids or tuple(sorted(recorded))
            digest_payload = "|".join((review.concept.id, review.state, *evidence))
            identifier = "review_" + hashlib.sha256(digest_payload.encode("utf-8")).hexdigest()[:24]
            try:
                logs.append(self.memory.get(identifier, record_access=False))
                continue
            except KeyError:
                pass
            logs.append(self.memory.add(
                f"Concept review: {review.concept.id} is {review.state}",
                kind="concept_review",
                source_uri="mnn://concept-reviewer/v1",
                importance=0.7 if review.state in {"conflicted", "stale", "unverified"} else 0.4,
                confidence=1.0,
                tags=("concept-review", review.state),
                related_ids=(review.concept.id, *evidence),
                metadata={
                    "reviewed_concept_id": review.concept.id,
                    "state": review.state,
                    "current_evidence_ids": list(review.current_evidence_ids),
                    "added_evidence_ids": list(review.added_evidence_ids),
                    "missing_evidence_ids": list(review.missing_evidence_ids),
                    "current_status": review.current_status,
                    "explanation": review.explanation,
                    "reviewer_schema_version": self.schema_version,
                },
                fragment_id=identifier,
            ))
        return logs
