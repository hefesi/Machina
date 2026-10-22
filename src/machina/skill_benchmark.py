"""A small, objectively scored text-retrieval skill for D2.2.

The benchmark deliberately supports a narrow, explicit input format. It is
designed to test whether strategy feedback improves a useful task on unseen
records and whether that improvement survives process-style restart via SQLite.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalTask:
    task_type: str
    context: str
    question: str
    expected_answer: str


def _query_parts(question: str) -> tuple[str, str]:
    match = re.fullmatch(
        r"\s*What is the ([a-z][a-z ]*?) for ([A-Za-z][A-Za-z0-9 _-]*)\?\s*",
        question,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError("question must look like 'What is the <field> for <entity>?'")
    return match.group(1).strip().lower(), match.group(2).strip()


def _first_context_value(context: str) -> str | None:
    """Naive direct strategy: return the first value, without query matching."""
    prose = re.search(r"\bis\s+([^.;\n]+)", context, flags=re.IGNORECASE)
    if prose:
        return prose.group(1).strip()
    for line in context.splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) >= 3 and cells[0].lower() not in {"entity", "person", "project"}:
            return cells[-1]
    return None


def _decompose_retrieval(context: str, field: str, entity: str) -> str | None:
    """Decompose the query into entity + field, then inspect matching sentences."""
    pattern = re.compile(
        rf"\b{re.escape(entity)}'s\s+{re.escape(field)}\s+is\s+([^.;\n]+)",
        flags=re.IGNORECASE,
    )
    for sentence in re.split(r"(?<=[.!?])\s+|\n+", context):
        match = pattern.search(sentence)
        if match:
            return match.group(1).strip()
    return None


def _checklist_retrieval(context: str, field: str, entity: str) -> str | None:
    """Scan structured rows and require both entity and field to match."""
    for line in context.splitlines():
        cells = [cell.strip() for cell in line.split("|")]
        if len(cells) < 3:
            continue
        if cells[0].casefold() == entity.casefold() and cells[1].casefold() == field.casefold():
            return cells[2]
    return None


def solve(task: RetrievalTask, strategy: str) -> str | None:
    """Execute one candidate strategy; expected answers are never passed to it."""
    field, entity = _query_parts(task.question)
    if strategy == "direct":
        return _first_context_value(task.context)
    if strategy == "decompose":
        return _decompose_retrieval(task.context, field, entity)
    if strategy == "checklist":
        return _checklist_retrieval(task.context, field, entity)
    raise ValueError(f"unknown strategy: {strategy}")


def score(task: RetrievalTask, strategy: str) -> float:
    """Exact-match reward from 0.0 to 1.0, computed by the evaluation environment."""
    prediction = solve(task, strategy)
    return float(prediction is not None and prediction.casefold() == task.expected_answer.casefold())
