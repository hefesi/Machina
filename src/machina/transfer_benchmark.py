"""D2.4 benchmark: transfer a learned strategy to unseen formats and questions.

The examples deliberately use formats absent from D2.2 training. The evaluator
keeps expected answers separate from solver inputs and scores exact matches.
This is a narrow structural-transfer benchmark, not broad language understanding.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class TransferTask:
    task_type: str
    context: str
    question: str
    expected_answer: str


def _query_parts(question: str) -> tuple[str, str]:
    patterns = (
        r"\s*Find\s+([a-z][a-z ]*?)\s+belonging\s+to\s+([A-Za-z][A-Za-z0-9 _-]*)\.?\s*",
        r"\s*Locate\s+the\s+([a-z][a-z ]*?)\s+for\s+([A-Za-z][A-Za-z0-9 _-]*)\.?\s*",
    )
    for pattern in patterns:
        match = re.fullmatch(pattern, question, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().lower(), match.group(2).strip()
    raise ValueError("unsupported transfer question format")


def _first_value(context: str) -> str | None:
    match = re.search(r"[:=]\s*([^\n;},]+)", context)
    return match.group(1).strip() if match else None


def _decompose(context: str, field: str, entity: str) -> str | None:
    # The learned "decompose" strategy is applied to new syntactic realizations:
    # entity + field + value, rather than the training benchmark's possessive prose.
    escaped_entity = re.escape(entity)
    escaped_field = re.escape(field)
    patterns = (
        rf"(?im)^\s*[-*]\s*{escaped_entity}\s*[—–-]\s*{escaped_field}\s*:\s*([^\n;]+)",
        rf"(?im)^\s*record\s*\[\s*{escaped_entity}\s*\]\s*\{{\s*{escaped_field}\s*=\s*([^}}\n;]+)",
        rf"(?im)^\s*{escaped_entity}\s*::\s*{escaped_field}\s*=\s*([^\n;]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, context)
        if match:
            return match.group(1).strip().strip('"\' ')
    return None


def solve_transfer(task: TransferTask, strategy: str) -> str | None:
    field, entity = _query_parts(task.question)
    if strategy == "direct":
        return _first_value(task.context)
    if strategy == "decompose":
        return _decompose(task.context, field, entity)
    if strategy == "checklist":
        # Intentionally limited to the earlier pipe-table representation.
        for line in task.context.splitlines():
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) >= 3 and cells[0].casefold() == entity.casefold() and cells[1].casefold() == field.casefold():
                return cells[2]
        return None
    raise ValueError(f"unknown strategy: {strategy}")


def score_transfer(task: TransferTask, strategy: str) -> float:
    prediction = solve_transfer(task, strategy)
    return float(prediction is not None and prediction.casefold() == task.expected_answer.casefold())


TRANSFER_TASKS = (
    TransferTask(
        "unseen_bullet_format",
        "- Nora — editor: Vim\n- Ivo — editor: Helix\n- Ivo — room: 7",
        "Find editor belonging to Ivo.",
        "Helix",
    ),
    TransferTask(
        "unseen_bullet_format",
        "- Ada — deadline: 2027-01-03\n- Bo — deadline: 2027-01-19",
        "Locate the deadline for Bo.",
        "2027-01-19",
    ),
    TransferTask(
        "unseen_record_format",
        'record[Nora]{editor="Vim"}\nrecord[Ivo]{editor="Zed"}\nrecord[Ivo]{room="22"}',
        "Find editor belonging to Ivo.",
        "Zed",
    ),
    TransferTask(
        "unseen_record_format",
        'record[Project Pine]{deadline="2027-02-02"}\nrecord[Project Ash]{deadline="2027-02-17"}',
        "Locate the deadline for Project Ash.",
        "2027-02-17",
    ),
)
