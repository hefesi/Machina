# MNN memory retrieval feedback v0.1

## Purpose

MNNMemoryRetrievalFeedback provides an explicit feedback loop between a retrieval result and the existing SQLite-backed FragmentMemory.

- Positive usefulness feedback raises a fragment's retrieval importance.
- Negative usefulness feedback lowers importance, but does not claim the content is false. For explicitly pinned fragments, negative feedback leaves importance unchanged to protect critical knowledge.
- Content, provenance, confidence, associations, and pin state are left unchanged.
- Importance remains bounded to [0, 1] and is persisted by the existing memory store.
- The result object records the applied signal and before/after importance for caller-side logging, plus `feedback_id` and `applied` to distinguish a new update from an idempotent replay.
- `apply_many()` accepts explicit per-fragment labels and validates every ID and label before the first update; it does not blindly reward all recalled fragments.
- Supplying `feedback_id` persists the batch and its before/after values in the same SQLite database as the fragments. Retrying the same ID and payload is idempotent; reusing the ID with different feedback is rejected.

## Example

```python
from machina.fragment_memory import FragmentMemory
from machina.mnn_memory_retrieval_feedback import MNNMemoryRetrievalFeedback

with FragmentMemory("data/machina-memory.sqlite3") as memory:
    feedback = MNNMemoryRetrievalFeedback(memory, default_strength=0.1)
    updated, event = feedback.apply("fragment-id", useful=True)
    print(event.importance_before, event.importance_after)
```

## VirtualBrain integration

When `VirtualBrain` is configured with `fragment_memory_path`, a caller can
submit explicit feedback for fragments actually returned by a cycle's
`memory.retrieved` event:

```python
cycle = brain.run_cycle("Recall the sensor calibration", "Use calibration")
feedback_event = brain.apply_retrieval_feedback(
    cycle.cycle_id,
    {"fragment-id-returned-by-this-cycle": True},
    strength=0.1,
)
```

The method records a `memory.retrieval_feedback_applied` artifact in the
append-only event journal. It uses a stable per-cycle operation ID by default,
so retrying after a partial failure between the fragment database and event
journal does not apply the importance delta twice. A caller may provide an
explicit `feedback_id`. Only one feedback batch is accepted per cycle, and
only IDs in that cycle's retrieved fragment context can be rated. Because the
fragment archive and event journal are separate SQLite databases, this is a
retry-safe two-write protocol, not a single cross-database atomic transaction.

## Important distinction

Usefulness is task-relative. A memory can be unhelpful for one query and still be true or important in another context. Callers should send feedback only when a retrieval outcome has been observed; do not treat lack of retrieval or low lexical overlap as proof that a memory should be forgotten. Pinned records remain pinned, and this component never deletes archived fragments.

## Validation

Unit tests cover positive/negative feedback, persistence across reopen, bounds, invalid inputs, missing fragment IDs, mixed batch updates, prevalidation, and idempotent retries using `feedback_id`. The feedback ledger and importance updates are committed in one SQLite transaction. Integration tests verify that feedback can change subsequent lexical recall ranking, that the ranking survives a database restart, and that pinned memory is protected from negative feedback. Run with:
python -m unittest tests.test_mnn_memory_retrieval_feedback

## Retrieval evaluation

`machina.mnn_retrieval_evaluation.evaluate_retrieval()` provides a deterministic baseline for measuring recall ranking against explicit relevant fragment IDs. It reports precision@k, recall@k, and reciprocal rank (MRR for a single query). The evaluator does not infer which records are relevant and does not modify memory; relevance labels must come from a test fixture or an observed task outcome.

Example:

```python
from machina.mnn_retrieval_evaluation import evaluate_retrieval

result = evaluate_retrieval(
    memory,
    "Recall the sensor calibration",
    relevant_ids=["calibration-fragment"],
    k=5,
)
print(result.precision_at_k, result.recall_at_k, result.reciprocal_rank)
```

The integration test compares metrics before and after explicit feedback, then reopens the SQLite database and checks that the ranking persists. This distinguishes a measurable ranking improvement from merely changing an internal importance value.

For a fixed benchmark with multiple queries, `evaluate_retrieval_suite(memory, judgments, k=5)` accepts a mapping from each query to its known relevant IDs and returns macro-averaged precision@k, recall@k, and mean reciprocal rank. Each query receives equal weight, which helps expose regressions that a single hand-picked example can hide. Keep the query set and relevance judgments fixed when comparing versions.
