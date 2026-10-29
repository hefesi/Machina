from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_retrieval_evaluation import (
    compare_retrieval_suites,
    evaluate_retrieval,
    evaluate_retrieval_suite,
    run_retrieval_feedback_experiment,
)


class RetrievalEvaluationTests(unittest.TestCase):
    def test_metrics_reflect_feedback_and_survive_restart(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            with FragmentMemory(path) as memory:
                memory.add(
                    "alpha beta task memory",
                    source_uri="test://relevant",
                    importance=0.1,
                    confidence=0.5,
                    fragment_id="relevant",
                )
                memory.add(
                    "alpha beta task memory",
                    source_uri="test://distractor",
                    importance=0.2,
                    confidence=0.5,
                    fragment_id="distractor",
                )
                before = evaluate_retrieval(memory, "alpha beta task", ["relevant"], k=2)
                self.assertEqual(("distractor", "relevant"), before.retrieved_ids)
                self.assertEqual(0.5, before.precision_at_k)
                self.assertEqual(1.0, before.recall_at_k)
                self.assertEqual(0.5, before.reciprocal_rank)

                from machina.mnn_memory_retrieval_feedback import MNNMemoryRetrievalFeedback
                MNNMemoryRetrievalFeedback(memory).apply(
                    "relevant", useful=True, strength=0.9, feedback_id="eval-feedback-1"
                )
                after = evaluate_retrieval(memory, "alpha beta task", ["relevant"], k=2)
                self.assertEqual(("relevant", "distractor"), after.retrieved_ids)
                self.assertEqual(0.5, after.precision_at_k)
                self.assertEqual(1.0, after.recall_at_k)
                self.assertEqual(1.0, after.reciprocal_rank)

            with FragmentMemory(path) as restarted:
                after_restart = evaluate_retrieval(
                    restarted, "alpha beta task", ["relevant"], k=2
                )
                self.assertEqual(after.retrieved_ids, after_restart.retrieved_ids)
                self.assertEqual(after.reciprocal_rank, after_restart.reciprocal_rank)

    def test_query_suite_reports_macro_averages(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with FragmentMemory(Path(directory) / "memory.sqlite3") as memory:
                memory.add(
                    "solar panel output efficiency",
                    source_uri="test://solar",
                    fragment_id="solar",
                )
                memory.add(
                    "ocean current marine biology",
                    source_uri="test://ocean",
                    fragment_id="ocean",
                )
                result = evaluate_retrieval_suite(
                    memory,
                    {
                        "solar panel efficiency": ["solar"],
                        "ocean current biology": ["ocean"],
                        # This query should count as a miss rather than being hidden
                        # by the two successful queries above.
                        "quantum computing hardware": ["solar"],
                    },
                    k=1,
                )
                self.assertEqual(3, len(result.evaluations))
                self.assertAlmostEqual(2 / 3, result.precision_at_k)
                self.assertAlmostEqual(2 / 3, result.recall_at_k)
                self.assertAlmostEqual(2 / 3, result.mean_reciprocal_rank)
                self.assertEqual((), result.evaluations[2].retrieved_ids)

                with self.assertRaises(ValueError):
                    evaluate_retrieval_suite(memory, {}, k=1)

    def test_suite_comparison_detects_improvement_without_hiding_control_query(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with FragmentMemory(Path(directory) / "memory.sqlite3") as memory:
                memory.add(
                    "alpha beta task memory",
                    source_uri="test://relevant",
                    importance=0.1,
                    confidence=0.5,
                    fragment_id="relevant",
                )
                memory.add(
                    "alpha beta task memory",
                    source_uri="test://distractor",
                    importance=0.2,
                    confidence=0.5,
                    fragment_id="distractor",
                )
                memory.add(
                    "solar panel efficiency",
                    source_uri="test://solar",
                    fragment_id="solar",
                )
                judgments = {
                    "alpha beta task": ["relevant"],
                    "solar panel efficiency": ["solar"],
                }
                before = evaluate_retrieval_suite(memory, judgments, k=2)

                from machina.mnn_memory_retrieval_feedback import MNNMemoryRetrievalFeedback
                MNNMemoryRetrievalFeedback(memory).apply(
                    "relevant", useful=True, strength=0.9, feedback_id="suite-comparison-feedback"
                )
                after = evaluate_retrieval_suite(memory, judgments, k=2)
                comparison = compare_retrieval_suites(before, after)

                self.assertEqual(("alpha beta task",), comparison.improved_queries)
                self.assertEqual(("solar panel efficiency",), comparison.unchanged_queries)
                self.assertEqual((), comparison.regressed_queries)
                self.assertEqual((), comparison.mixed_queries)
                self.assertGreater(comparison.mean_reciprocal_rank_delta, 0.0)

                incompatible_k = evaluate_retrieval_suite(memory, judgments, k=1)
                with self.assertRaises(ValueError):
                    compare_retrieval_suites(before, incompatible_k)

    def test_negative_feedback_reorders_distractor_without_rewriting_memory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with FragmentMemory(Path(directory) / "memory.sqlite3") as memory:
                relevant = memory.add(
                    "alpha beta task memory",
                    source_uri="test://relevant",
                    importance=0.2,
                    confidence=0.83,
                    tags=["calibration"],
                    metadata={"evidence": "observed"},
                    fragment_id="relevant",
                )
                distractor = memory.add(
                    "alpha beta task memory",
                    source_uri="test://distractor",
                    importance=0.8,
                    confidence=0.61,
                    tags=["archive"],
                    metadata={"evidence": "historical"},
                    fragment_id="distractor",
                )
                before = evaluate_retrieval(memory, "alpha beta task", ["relevant"], k=2)
                self.assertEqual(("distractor", "relevant"), before.retrieved_ids)

                from machina.mnn_memory_retrieval_feedback import MNNMemoryRetrievalFeedback
                MNNMemoryRetrievalFeedback(memory).apply(
                    "distractor",
                    useful=False,
                    strength=0.8,
                    feedback_id="negative-feedback-1",
                )
                after = evaluate_retrieval(memory, "alpha beta task", ["relevant"], k=2)
                self.assertEqual(("relevant", "distractor"), after.retrieved_ids)
                self.assertGreater(after.reciprocal_rank, before.reciprocal_rank)

                saved_relevant = memory.get("relevant", record_access=False)
                saved_distractor = memory.get("distractor", record_access=False)
                self.assertEqual(relevant.content, saved_relevant.content)
                self.assertEqual(relevant.source_uri, saved_relevant.source_uri)
                self.assertEqual(relevant.confidence, saved_relevant.confidence)
                self.assertEqual(relevant.tags, saved_relevant.tags)
                self.assertEqual(dict(relevant.metadata), dict(saved_relevant.metadata))
                self.assertEqual(distractor.content, saved_distractor.content)
                self.assertEqual(distractor.source_uri, saved_distractor.source_uri)
                self.assertEqual(distractor.confidence, saved_distractor.confidence)
                self.assertEqual(distractor.tags, saved_distractor.tags)
                self.assertEqual(dict(distractor.metadata), dict(saved_distractor.metadata))
                self.assertAlmostEqual(0.0, saved_distractor.importance)

    def test_feedback_experiment_measures_learning_and_rejects_unretrieved_fragment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with FragmentMemory(Path(directory) / "memory.sqlite3") as memory:
                memory.add(
                    "alpha beta task memory", source_uri="test://relevant",
                    importance=0.1, confidence=0.5, fragment_id="relevant",
                )
                memory.add(
                    "alpha beta task memory", source_uri="test://distractor",
                    importance=0.2, confidence=0.5, fragment_id="distractor",
                )
                memory.add(
                    "solar panel efficiency", source_uri="test://control",
                    fragment_id="control",
                )
                judgments = {
                    "alpha beta task": ["relevant"],
                    "solar panel efficiency": ["control"],
                }
                with self.assertRaises(ValueError):
                    run_retrieval_feedback_experiment(
                        memory, feedback_query="alpha beta task",
                        outcomes={"control": True}, judgments=judgments,
                        feedback_id="bad-feedback", k=2,
                    )

                result = run_retrieval_feedback_experiment(
                    memory, feedback_query="alpha beta task",
                    outcomes={"relevant": True}, judgments=judgments,
                    strength=0.9, feedback_id="experiment-feedback", k=2,
                )
                self.assertEqual("experiment-feedback", result.feedback_results[0].feedback_id)
                self.assertTrue(result.feedback_results[0].applied)
                self.assertEqual(("alpha beta task",), result.comparison.improved_queries)
                self.assertEqual(("solar panel efficiency",), result.comparison.unchanged_queries)
                self.assertGreater(result.comparison.mean_reciprocal_rank_delta, 0.0)

    def test_evaluation_rejects_invalid_judgments(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with FragmentMemory(Path(directory) / "memory.sqlite3") as memory:
                with self.assertRaises(ValueError):
                    evaluate_retrieval(memory, "query", [], k=2)
                with self.assertRaises(ValueError):
                    evaluate_retrieval(memory, "query", ["valid"], k=0)
                with self.assertRaises(ValueError):
                    evaluate_retrieval(memory, "query", "not-a-list", k=2)


if __name__ == "__main__":
    unittest.main()
