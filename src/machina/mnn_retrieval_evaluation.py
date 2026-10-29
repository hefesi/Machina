"""Deterministic metrics for evaluating MNN fragment retrieval.

These metrics measure ranking against caller-supplied relevant fragment IDs.
They do not infer relevance or claim semantic understanding.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Iterable

from .fragment_memory import FragmentMemory


@dataclass(frozen=True, slots=True)
class RetrievalEvaluation:
    """Ranking metrics for one query and an explicit relevance judgment."""

    query: str
    relevant_ids: tuple[str, ...]
    retrieved_ids: tuple[str, ...]
    hits: int
    precision_at_k: float
    recall_at_k: float
    reciprocal_rank: float


@dataclass(frozen=True, slots=True)
class RetrievalSuiteEvaluation:
    """Macro-averaged metrics across a fixed set of labeled queries."""

    evaluations: tuple[RetrievalEvaluation, ...]
    precision_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float


def evaluate_retrieval(
    memory: FragmentMemory,
    query: str,
    relevant_ids: Iterable[str],
    *,
    k: int = 5,
) -> RetrievalEvaluation:
    """Evaluate lexical retrieval using explicit relevant fragment IDs.

    Precision@k is hits divided by k, recall@k is hits divided by the number
    of relevant IDs, and reciprocal rank
    is the inverse rank of the first relevant result (zero if none is found).
    This function does not modify the memory or learn from the labels.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if isinstance(k, bool) or not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer")
    if isinstance(relevant_ids, (str, bytes)):
        raise ValueError("relevant_ids must be an iterable of fragment IDs, not a string")
    try:
        relevant = tuple(dict.fromkeys(relevant_ids))
    except TypeError as error:
        raise ValueError("relevant_ids must be an iterable of fragment IDs") from error
    if not relevant:
        raise ValueError("relevant_ids must not be empty")
    if any(not isinstance(item, str) or not item.strip() for item in relevant):
        raise ValueError("relevant_ids must contain non-empty strings")

    retrieved = tuple(item.id for item in memory.recall(query, limit=k))
    relevant_set = set(relevant)
    hits = sum(item_id in relevant_set for item_id in retrieved)
    precision = hits / k
    recall = hits / len(relevant)
    reciprocal_rank = next(
        (1.0 / rank for rank, item_id in enumerate(retrieved, start=1) if item_id in relevant_set),
        0.0,
    )
    # Guard the public result contract against accidental non-finite metrics.
    if not all(math.isfinite(value) for value in (precision, recall, reciprocal_rank)):
        raise RuntimeError("retrieval metrics must be finite")
    return RetrievalEvaluation(
        query=query.strip(),
        relevant_ids=relevant,
        retrieved_ids=retrieved,
        hits=hits,
        precision_at_k=precision,
        recall_at_k=recall,
        reciprocal_rank=reciprocal_rank,
    )


def evaluate_retrieval_suite(
    memory: FragmentMemory,
    judgments: Mapping[str, Iterable[str]],
    *,
    k: int = 5,
) -> RetrievalSuiteEvaluation:
    """Evaluate a fixed query set and return macro-averaged ranking metrics.

    `judgments` maps each query to its explicitly relevant fragment IDs.
    Every query contributes equally to the macro average. No feedback is
    applied and the memory is not modified.
    """
    if not isinstance(judgments, Mapping) or not judgments:
        raise ValueError("judgments must be a non-empty mapping of queries to relevant IDs")
    evaluations = tuple(
        evaluate_retrieval(memory, query, relevant_ids, k=k)
        for query, relevant_ids in judgments.items()
    )
    count = len(evaluations)
    return RetrievalSuiteEvaluation(
        evaluations=evaluations,
        precision_at_k=sum(item.precision_at_k for item in evaluations) / count,
        recall_at_k=sum(item.recall_at_k for item in evaluations) / count,
        mean_reciprocal_rank=sum(item.reciprocal_rank for item in evaluations) / count,
    )
