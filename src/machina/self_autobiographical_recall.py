"""Search traceable autobiographical transformations by lexical relevance.

This is an explainable retrieval baseline, not semantic understanding. It
returns journal provenance and only explicitly linked experience records.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

from .self_experience_integration import SelfExperienceIntegrator


@dataclass(frozen=True)
class SelfAutobiographicalMatch:
    transformation_event_id: str
    cycle_id: str
    sequence: int
    score: float
    matched_terms: tuple[str, ...]
    changed_paths: tuple[str, ...]
    durability: dict[str, dict[str, Any]]
    experience_records: tuple[dict[str, Any], ...]
    evidence_refs: tuple[str, ...]


class SelfAutobiographicalRecall:
    """Retrieve prior Self transformations and their explicitly linked episodes."""

    _TOKEN = re.compile(r"[a-zA-ZÀ-ÿ0-9_]{2,}", re.UNICODE)

    def __init__(self, integrator: SelfExperienceIntegrator) -> None:
        if not isinstance(integrator, SelfExperienceIntegrator):
            raise TypeError("integrator must be a SelfExperienceIntegrator")
        self.integrator = integrator

    @classmethod
    def _tokens(cls, value: Any) -> set[str]:
        if isinstance(value, (dict, list, tuple)):
            value = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
        return {token.casefold() for token in cls._TOKEN.findall(str(value))}

    def recall(self, query: str, *, limit: int = 5) -> tuple[SelfAutobiographicalMatch, ...]:
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be non-empty")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        query_terms = self._tokens(query)
        if not query_terms:
            return ()
        timeline = self.integrator.autobiography.timeline()
        records = {item["event_id"]: item for item in timeline}
        matches: list[SelfAutobiographicalMatch] = []
        for item in self.integrator.integrate()["transformations"]:
            event = records.get(item["event_id"])
            if event is None:
                continue
            experience_records = tuple(
                {
                    "event_id": link["event_id"],
                    "event_type": link["event_type"],
                    "link_basis": link["link_basis"],
                    "cycle_id": records[link["event_id"]]["cycle_id"],
                    "content": records[link["event_id"]]["content"],
                }
                for link in item["experience_links"]
                if link["event_id"] in records
            )
            searchable = {
                "trigger": item.get("trigger"),
                "changes": item.get("changes", {}),
                "durability": item.get("durability", {}),
                "experiences": [record["content"] for record in experience_records],
            }
            matched = query_terms & self._tokens(searchable)
            if not matched:
                continue
            score = len(matched) / len(query_terms)
            matches.append(SelfAutobiographicalMatch(
                transformation_event_id=item["event_id"],
                cycle_id=item["cycle_id"],
                sequence=item["sequence"],
                score=score,
                matched_terms=tuple(sorted(matched)),
                changed_paths=tuple(sorted(item.get("changes", {}))),
                durability=dict(item.get("durability", {})),
                experience_records=experience_records,
                evidence_refs=tuple(sorted(set(item.get("evidence_refs", [])))),
            ))
        matches.sort(key=lambda result: (-result.score, -result.sequence, result.transformation_event_id))
        return tuple(matches[:limit])
