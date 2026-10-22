"""D2.5: conservative decision policy with explicit abstention.

This policy only resolves fields supported by the narrow transfer benchmark.
It does not estimate calibrated probabilistic confidence: confidence is a
transparent evidence score based on candidate uniqueness.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from machina.transfer_benchmark import TransferTask, _query_parts


@dataclass(frozen=True)
class Decision:
    answer: str | None
    confidence: float
    status: str
    candidates: tuple[str, ...]


def _matching_values(task: TransferTask) -> tuple[str, ...]:
    field, entity = _query_parts(task.question)
    entity_pattern = re.escape(entity)
    field_pattern = re.escape(field)
    patterns = (
        rf"(?im)^\s*[-*]\s*{entity_pattern}\s*[—–-]\s*{field_pattern}\s*:\s*([^\n;]+)",
        rf"(?im)^\s*record\s*\[\s*{entity_pattern}\s*\]\s*\{{\s*{field_pattern}\s*=\s*([^}}\n;]+)",
        rf"(?im)^\s*{entity_pattern}\s*::\s*{field_pattern}\s*=\s*([^\n;]+)",
    )
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, task.context):
            value = match.group(1).strip().strip('"\\' ')
            if value:
                found.append(value)
    # Preserve order while deduplicating equivalent answers.
    unique: list[str] = []
    for value in found:
        if value.casefold() not in {item.casefold() for item in unique}:
            unique.append(value)
    return tuple(unique)


def decide(task: TransferTask) -> Decision:
    """Answer only when the requested entity/field has one unambiguous value.

    Confidence is 1.0 for one unique supported value and 0.0 for no evidence or
    conflicting values. Ambiguous/unsupported cases abstain instead of guessing.
    """
    candidates = _matching_values(task)
    if len(candidates) == 1:
        return Decision(candidates[0], 1.0, "answered", candidates)
    if not candidates:
        return Decision(None, 0.0, "abstained_no_evidence", candidates)
    return Decision(None, 0.0, "abstained_ambiguous", candidates)
