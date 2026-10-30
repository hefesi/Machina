"""Explicit, provenance-backed relations between persisted concept hypotheses.

Relations are supplied by an evaluator; this module does not infer semantic
relationships from wording. Records are append-only FragmentMemory entries.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Literal

from .fragment_memory import FragmentMemory, MemoryFragment

ConceptRelationKind = Literal["supports", "contradicts", "contextualizes", "competes_with"]


@dataclass(frozen=True, slots=True)
class ConceptRelation:
    relation_id: str
    source_concept_id: str
    target_concept_id: str
    relationship: ConceptRelationKind
    evidence_ids: tuple[str, ...]
    context_refs: tuple[str, ...]


class MNNConceptRelationStore:
    """Persist explicit relations while preserving competing concept records."""

    _KINDS = {"supports", "contradicts", "contextualizes", "competes_with"}

    def __init__(self, memory: FragmentMemory) -> None:
        if not isinstance(memory, FragmentMemory):
            raise TypeError("memory must be a FragmentMemory")
        self.memory = memory

    def add(
        self,
        source_concept_id: str,
        target_concept_id: str,
        relationship: ConceptRelationKind,
        *,
        evidence_ids: tuple[str, ...],
        context_refs: tuple[str, ...] = (),
    ) -> ConceptRelation:
        for name, value in (("source_concept_id", source_concept_id), ("target_concept_id", target_concept_id)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a non-empty string")
        if source_concept_id == target_concept_id:
            raise ValueError("a concept cannot be related to itself")
        if relationship not in self._KINDS:
            raise ValueError(f"relationship must be one of {sorted(self._KINDS)}")
        for name, values in (("evidence_ids", evidence_ids), ("context_refs", context_refs)):
            if isinstance(values, (str, bytes)) or not isinstance(values, (tuple, list)):
                raise TypeError(f"{name} must be a tuple or list")
            if any(not isinstance(item, str) or not item.strip() for item in values):
                raise ValueError(f"{name} must contain non-empty strings")
        if not evidence_ids:
            raise ValueError("at least one evidence ID is required")

        source = self.memory.get(source_concept_id, record_access=False)
        target = self.memory.get(target_concept_id, record_access=False)
        if source.kind != "concept" or target.kind != "concept":
            raise ValueError("both endpoints must be persisted concept fragments")
        existing_ids = {item.id for item in self.memory.archive()}
        missing = set(evidence_ids) - existing_ids
        if missing:
            raise ValueError(f"missing evidence fragments: {', '.join(sorted(missing))}")

        evidence = tuple(sorted(set(evidence_ids)))
        contexts = tuple(sorted(set(context_refs)))
        payload = "|".join((source_concept_id, target_concept_id, relationship, *evidence, "--", *contexts))
        relation_id = "concept_relation_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]
        try:
            fragment = self.memory.get(relation_id, record_access=False)
        except KeyError:
            fragment = self.memory.add(
                f"Concept relation: {source_concept_id} {relationship} {target_concept_id}",
                kind="concept_relation",
                source_uri="mnn://concept-relations/v1",
                importance=0.65,
                confidence=1.0,
                tags=("concept-relation", relationship),
                related_ids=(source_concept_id, target_concept_id, *evidence),
                metadata={
                    "source_concept_id": source_concept_id,
                    "target_concept_id": target_concept_id,
                    "relationship": relationship,
                    "evidence_ids": list(evidence),
                    "context_refs": list(contexts),
                    "relationship_was_inferred": False,
                    "schema_version": 1,
                },
                fragment_id=relation_id,
            )
        return self._from_fragment(fragment)

    def for_concept(self, concept_id: str) -> list[ConceptRelation]:
        if not isinstance(concept_id, str) or not concept_id.strip():
            raise ValueError("concept_id must be a non-empty string")
        matches = [
            item for item in self.memory.archive()
            if item.kind == "concept_relation"
            and concept_id in {
                item.metadata.get("source_concept_id"),
                item.metadata.get("target_concept_id"),
            }
        ]
        return [self._from_fragment(item) for item in sorted(matches, key=lambda item: item.id)]

    @staticmethod
    def _from_fragment(fragment: MemoryFragment) -> ConceptRelation:
        metadata = fragment.metadata
        return ConceptRelation(
            relation_id=fragment.id,
            source_concept_id=metadata["source_concept_id"],
            target_concept_id=metadata["target_concept_id"],
            relationship=metadata["relationship"],
            evidence_ids=tuple(metadata["evidence_ids"]),
            context_refs=tuple(metadata.get("context_refs", ())),
        )
