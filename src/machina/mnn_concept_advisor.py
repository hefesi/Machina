"""Conservative, provenance-aware action guidance from reviewed MNN concepts.

Concepts are not actions by themselves. This advisor requires an explicit
concept-key -> action mapping supplied by the application, and abstains when
the matching concept is stale, conflicted, unsupported, or ambiguous.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Iterable

from .fragment_memory import FragmentMemory
from .mnn_concept_review import MNNConceptReviewer


@dataclass(frozen=True, slots=True)
class ConceptRecommendation:
    """An explicit action suggestion with traceable concept and evidence IDs."""

    action: str
    concept_key: str
    concept_id: str
    evidence_ids: tuple[str, ...]
    confidence: float
    method: str = "explicit-mapping-over-current-reviewed-concept"


class MNNConceptAdvisor:
    """Map current supported concepts to configured actions; never infer mappings."""

    def __init__(
        self,
        memory: FragmentMemory,
        action_by_concept: Mapping[str, str],
        *,
        min_confidence: float = 0.0,
        min_support: int = 2,
    ) -> None:
        if not isinstance(action_by_concept, Mapping) or not action_by_concept:
            raise ValueError("action_by_concept must be a non-empty mapping")
        normalized: dict[str, str] = {}
        for key, action in action_by_concept.items():
            if not isinstance(key, str) or not key.strip():
                raise ValueError("concept keys must be non-empty strings")
            if not isinstance(action, str) or not action.strip():
                raise ValueError("mapped actions must be non-empty strings")
            normalized[" ".join(key.casefold().split())] = action.strip()
        if len(normalized) != len(action_by_concept):
            raise ValueError("concept keys must be unique after normalization")
        if isinstance(min_confidence, bool) or not isinstance(min_confidence, (int, float)) or not math.isfinite(min_confidence) or not 0.0 <= min_confidence <= 1.0:
            raise ValueError("min_confidence must be finite and in [0, 1]")
        self.memory = memory
        self.action_by_concept = normalized
        self.min_confidence = float(min_confidence)
        self.reviewer = MNNConceptReviewer(memory, min_support=min_support)

    def recommend(self, context_tags: Iterable[str]) -> dict:
        """Return a recommendation or an explicit abstention with reasons.

        Only exact normalized tag matches are considered. A matching concept is
        usable only when its latest review is current, its current status is
        supported, its provenance is present, and its heuristic confidence
        clears the configured threshold. Conflicting snapshots block the key.
        """
        if isinstance(context_tags, (str, bytes)):
            raise ValueError("context_tags must be an iterable of tags, not a string")
        tags: set[str] = set()
        try:
            for tag in context_tags:
                if not isinstance(tag, str) or not tag.strip():
                    raise ValueError("context tags must be non-empty strings")
                tags.add(" ".join(tag.casefold().split()))
        except TypeError as error:
            raise ValueError("context_tags must be an iterable of strings") from error

        matched_keys = sorted(tags & self.action_by_concept.keys())
        if not matched_keys:
            return {"recommendation": None, "status": "abstained", "reason": "no_configured_concept_match"}

        reviews = self.reviewer.review()
        candidates: list[ConceptRecommendation] = []
        blocked: dict[str, str] = {}
        for key in matched_keys:
            key_reviews = [
                item for item in reviews
                if item.concept.metadata.get("concept_key") == key
            ]
            if any(item.state == "conflicted" for item in key_reviews):
                blocked[key] = "conflicted_evidence"
                continue
            current = [
                item for item in key_reviews
                if item.state == "current" and item.current_status == "supported"
            ]
            if not current:
                blocked[key] = (
                    "stale_or_unverified_concept" if key_reviews
                    else "no_persisted_concept"
                )
                continue
            concept_review = sorted(current, key=lambda item: item.concept.id)[-1]
            concept = concept_review.concept
            confidence = concept.confidence
            evidence_ids = concept_review.current_evidence_ids
            if not evidence_ids:
                blocked[key] = "missing_evidence_provenance"
                continue
            if confidence < self.min_confidence:
                blocked[key] = "confidence_below_threshold"
                continue
            candidates.append(ConceptRecommendation(
                action=self.action_by_concept[key],
                concept_key=key,
                concept_id=concept.id,
                evidence_ids=evidence_ids,
                confidence=confidence,
            ))

        if blocked:
            return {
                "recommendation": None,
                "status": "abstained",
                "reason": "one_or_more_matching_concepts_are_not_safe_to_use",
                "blocked_concepts": blocked,
            }
        actions = {item.action for item in candidates}
        if len(actions) != 1:
            return {
                "recommendation": None,
                "status": "abstained",
                "reason": "ambiguous_action_mapping",
                "candidate_actions": sorted(actions),
            }
        # Multiple concepts may independently support the same configured action.
        # Return each provenance path instead of merging evidence into a fake score.
        return {
            "recommendation": {
                "action": candidates[0].action,
                "concepts": [
                    {
                        "key": item.concept_key,
                        "concept_id": item.concept_id,
                        "evidence_ids": list(item.evidence_ids),
                        "confidence": item.confidence,
                    }
                    for item in candidates
                ],
                "method": "explicit-mapping-over-current-reviewed-concept",
            },
            "status": "recommended",
            "reason": None,
        }
