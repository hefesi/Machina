"""Explainable context expansion and structured memory-conflict detection.

This module avoids claiming semantic understanding. Contextual retrieval expands
queries using caller-supplied aliases and existing explicit associations.
Conflict detection compares structured claims only.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Mapping, Sequence

from machina.fragment_memory import FragmentMemory, MemoryFragment


def _normalize(value: object) -> str:
    return " ".join(str(value).casefold().split())


def _terms(value: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"\w+", value, flags=re.UNICODE)
        if len(token) > 1
    }


@dataclass(frozen=True, slots=True)
class MemoryConflict:
    """Two sourced fragments assert different values for the same claim key."""

    subject: str
    predicate: str
    first_value: str
    second_value: str
    first_fragment_id: str
    second_fragment_id: str
    first_source_uri: str
    second_source_uri: str


def retrieve_context(
    memory: FragmentMemory,
    query: str,
    *,
    aliases: Mapping[str, Sequence[str]] | None = None,
    limit: int = 5,
    include_related: bool = True,
) -> list[MemoryFragment]:
    """Retrieve using direct wording, explicit aliases, and one-hop links.

    Aliases are explicit and deterministic; they are not learned synonymy or
    embedding-based semantic search. Results are deduplicated by fragment ID.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit must be a positive integer")

    query_terms = _terms(query)
    expansions: list[str] = [query]
    for key, values in (aliases or {}).items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("alias keys must be non-empty strings")
        if not all(isinstance(value, str) and value.strip() for value in values):
            raise ValueError("alias values must be non-empty strings")
        if _terms(key) & query_terms:
            expansions.extend(values)

    ordered: dict[str, MemoryFragment] = {}
    for expanded_query in expansions:
        for fragment in memory.recall(
            expanded_query, limit=max(limit, memory.count()), include_related=include_related
        ):
            ordered.setdefault(fragment.id, fragment)
    return list(ordered.values())[:limit]


def find_structured_conflicts(
    fragments: Sequence[MemoryFragment],
) -> list[MemoryConflict]:
    """Find differing values for identical explicit metadata claims.

    Each claim must contain non-empty subject, predicate and value strings.
    Natural-language contradiction inference is intentionally out of scope.
    """
    claims: dict[tuple[str, str], list[tuple[str, str, MemoryFragment]]] = {}
    for fragment in fragments:
        claim = fragment.metadata.get("claim")
        if not isinstance(claim, Mapping):
            continue
        if not all(
            isinstance(claim.get(field), str) and claim[field].strip()
            for field in ("subject", "predicate", "value")
        ):
            continue
        subject = _normalize(claim["subject"])
        predicate = _normalize(claim["predicate"])
        value = _normalize(claim["value"])
        claims.setdefault((subject, predicate), []).append((value, str(claim["value"]).strip(), fragment))

    conflicts: list[MemoryConflict] = []
    for (subject, predicate), entries in sorted(claims.items()):
        for index, (first_normalized, first_value, first_fragment) in enumerate(entries):
            for second_normalized, second_value, second_fragment in entries[index + 1:]:
                if first_normalized == second_normalized:
                    continue
                conflicts.append(MemoryConflict(
                    subject=subject,
                    predicate=predicate,
                    first_value=first_value,
                    second_value=second_value,
                    first_fragment_id=first_fragment.id,
                    second_fragment_id=second_fragment.id,
                    first_source_uri=first_fragment.source_uri,
                    second_source_uri=second_fragment.source_uri,
                ))
    return conflicts
