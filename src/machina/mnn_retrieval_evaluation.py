"""Deterministic metrics for evaluating MNN fragment retrieval.

These metrics measure ranking against caller-supplied relevant fragment IDs.
They do not infer relevance or claim semantic understanding.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from collections.abc import Iterable, Mapping

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
    k: int = 5


@dataclass(frozen=True, slots=True)
class RetrievalSuiteEvaluation:
    """Macro-averaged metrics across a fixed set of labeled queries."""

    evaluations: tuple[RetrievalEvaluation, ...]
    precision_at_k: float
    recall_at_k: float
    mean_reciprocal_rank: float


@dataclass(frozen=True, slots=True)
class RetrievalSuiteComparison:
    """Metric deltas and per-query changes between two fixed evaluations."""

    before: RetrievalSuiteEvaluation
    after: RetrievalSuiteEvaluation
    precision_delta: float
    recall_delta: float
    mean_reciprocal_rank_delta: float
    improved_queries: tuple[str, ...]
    regressed_queries: tuple[str, ...]
    mixed_queries: tuple[str, ...]
    unchanged_queries: tuple[str, ...]


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
        k=k,
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


def compare_retrieval_suites(
    before: RetrievalSuiteEvaluation,
    after: RetrievalSuiteEvaluation,
) -> RetrievalSuiteComparison:
    """Compare two evaluations made with identical queries, labels, and k.

    Per-query status is based on precision@k, recall@k, and reciprocal rank:
    a query is improved/regressed only when all metrics are non-worse and at
    least one is better/worse. Trade-offs are classified as mixed. This helper
    only compares saved results; it never mutates memory or applies feedback.
    """
    if not isinstance(before, RetrievalSuiteEvaluation) or not isinstance(after, RetrievalSuiteEvaluation):
        raise ValueError("before and after must be RetrievalSuiteEvaluation values")
    before_by_query = {item.query: item for item in before.evaluations}
    after_by_query = {item.query: item for item in after.evaluations}
    if not before_by_query or set(before_by_query) != set(after_by_query):
        raise ValueError("before and after must contain the same non-empty query set")

    improved: list[str] = []
    regressed: list[str] = []
    mixed: list[str] = []
    unchanged: list[str] = []
    epsilon = 1e-12
    for query, old in before_by_query.items():
        new = after_by_query[query]
        if old.relevant_ids != new.relevant_ids:
            raise ValueError(f"relevance judgments changed for query: {query}")
        if old.k != new.k:
            raise ValueError(f"k changed for query: {query}")
        old_metrics = (old.precision_at_k, old.recall_at_k, old.reciprocal_rank)
        new_metrics = (new.precision_at_k, new.recall_at_k, new.reciprocal_rank)
        deltas = tuple(new_value - old_value for old_value, new_value in zip(old_metrics, new_metrics))
        if all(delta >= -epsilon for delta in deltas) and any(delta > epsilon for delta in deltas):
            improved.append(query)
        elif all(delta <= epsilon for delta in deltas) and any(delta < -epsilon for delta in deltas):
            regressed.append(query)
        elif all(abs(delta) <= epsilon for delta in deltas):
            unchanged.append(query)
        else:
            mixed.append(query)

    return RetrievalSuiteComparison(
        before=before,
        after=after,
        precision_delta=after.precision_at_k - before.precision_at_k,
        recall_delta=after.recall_at_k - before.recall_at_k,
        mean_reciprocal_rank_delta=after.mean_reciprocal_rank - before.mean_reciprocal_rank,
        improved_queries=tuple(improved),
        regressed_queries=tuple(regressed),
        mixed_queries=tuple(mixed),
        unchanged_queries=tuple(unchanged),
    )
