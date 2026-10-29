# MNN memory retrieval feedback v0.1

## Purpose

MNNMemoryRetrievalFeedback provides an explicit feedback loop between a retrieval result and the existing SQLite-backed FragmentMemory.

- Positive usefulness feedback raises a fragment's retrieval importance.
- Negative usefulness feedback lowers importance, but does not claim the content is false. Pinning protects retention and active-view priority, not task relevance: pinned fragments can adapt their importance while remaining pinned and protected from active-view pruning.
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
only IDs in that cycle's retrieved fragment context can be rated.

Feedback is rejected until the cycle has both a persisted `action.result` and
an `evaluation.completed` artifact. The feedback artifact links to all three
records—the retrieval, action result, and evaluation—and snapshots the observed
action status/result plus evaluation success and prediction error. This gives
auditors a causal trail from recalled fragments to the outcome used when
adjusting their task-relative importance. It does **not** automatically infer
which fragment caused success or failure: callers must still provide explicit
per-fragment usefulness labels. Because the fragment archive and event journal
are separate SQLite databases, this is a retry-safe two-write protocol, not a
single cross-database atomic transaction.

## Contextual relevance

Global importance and task-relative relevance are separate signals. Use
`FragmentMemory.apply_context_feedback_batch()` to rate fragments within an
explicit context such as `"maintenance"` or `"research"`. Each unseen
(fragment, context) pair starts at neutral `0.5`; scores stay in `[0, 1]`.
The operation ID is idempotent, and reusing it with a different context or
label set is rejected.

Pass the same context to `recall(query, context="maintenance")` to apply the
context score as a bounded ranking adjustment. Context changes do not modify
global importance, content, confidence, provenance, tags, associations, or
pinning. A different context retains its own independent score. The adjustment
is deliberately limited so contextual preference cannot overwhelm lexical
evidence.

Every accepted update is also recorded in an append-only contextual audit
trail. Call `context_feedback_history(fragment_id, context, limit=50)` to
inspect the newest-first sequence, including the operation ID, usefulness
label, before/after scores and timestamp. Idempotent retries return the original
result and do not create duplicate history events. This makes score changes
inspectable across process restarts without treating the score as truth.

Contextual relevance can optionally decay toward neutral over time. By default,
decay is disabled to preserve existing ranking behavior. Enable it by passing
`context_decay_half_life_seconds` to `FragmentMemory`; for example, a half-life
of 86,400 seconds means the distance from the stored score to neutral 0.5 is
halved after one day. Scores above and below 0.5 both approach 0.5, so age alone
does not turn a memory into a negative signal. The decay is computed at read
time: persisted scores and audit events are not rewritten.

```python
from machina.fragment_memory import FragmentMemory

with FragmentMemory(
    "data/machina-memory.sqlite3",
    context_decay_half_life_seconds=86_400,
) as memory:
    score = memory.context_importance("calibration-fragment", "maintenance")
    results = memory.recall("sensor calibration", context="maintenance", limit=5)
```

For deterministic simulations, `context_importance()` accepts an aware
`datetime` through `as_of` and an optional per-call `half_life_seconds`
override. Context decay affects only the bounded contextual ranking adjustment;
it does not delete or edit memory content, global importance, provenance, or
pinning. Pinned memory remains protected by the active-view policy.

```python
scores, applied = memory.apply_context_feedback_batch(
    {"calibration-fragment": True, "outdated-fragment": False},
    context="sensor-maintenance",
    operation_id="maintenance-cycle-42",
    strength=0.2,
)
results = memory.recall(
    "sensor calibration", context="sensor-maintenance", limit=5
)
```

Usefulness is task-relative. A memory can be unhelpful for one query and still
be true or important in another context. Do not treat lack of retrieval or low
lexical overlap as proof that a memory should be forgotten. Pinned records
remain pinned and protected in the active view even if their task-relative
importance changes. This component never deletes archived fragments.

## Validation

Unit tests cover positive/negative feedback, persistence across reopen, bounds, invalid inputs, missing fragment IDs, mixed batch updates, prevalidation, and idempotent retries using `feedback_id`. The feedback ledger and importance updates are committed in one SQLite transaction. Integration tests verify that feedback can change subsequent lexical recall ranking, that the ranking survives a database restart, and that pinned memory remains pinned and active even when negative feedback lowers task-relative importance. Run with:
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


## Comparing before/after runs

Use `compare_retrieval_suites(before, after)` to compare two snapshots from the same fixed benchmark. Both snapshots must use the same query set, relevant fragment IDs, and `k`. The result reports macro-metric deltas and classifies each query as improved, regressed, mixed, or unchanged. A query is only called improved or regressed when all three per-query metrics move in the same direction or stay level; metric trade-offs are reported as mixed.

```python
from machina.mnn_retrieval_evaluation import (
    compare_retrieval_suites,
    evaluate_retrieval_suite,
)

judgments = {
    "sensor calibration": ["calibration-fragment"],
    "battery temperature": ["thermal-fragment"],
}

before = evaluate_retrieval_suite(memory, judgments, k=5)
# Apply explicit feedback based on an observed outcome.
after = evaluate_retrieval_suite(memory, judgments, k=5)
comparison = compare_retrieval_suites(before, after)

print(comparison.mean_reciprocal_rank_delta)
print(comparison.improved_queries, comparison.regressed_queries)
```

Capture `before` before changing importance and `after` only after feedback. The example above leaves the feedback call as an application-specific step because the feedback must be grounded in an observed outcome, not invented labels. This comparison is a measurement aid, not a learning algorithm by itself.


## End-to-end feedback experiment

`run_retrieval_feedback_experiment()` combines the measured loop: it verifies that every feedback target was retrieved for the supplied feedback query, captures the benchmark before feedback, applies one idempotent feedback batch, captures it again, and reports per-query and macro metric changes. Both feedback outcomes and relevance judgments remain explicit inputs; the helper does not infer task success.

```python
from machina.mnn_retrieval_evaluation import run_retrieval_feedback_experiment

result = run_retrieval_feedback_experiment(
    memory,
    feedback_query="Recall the sensor calibration",
    outcomes={"calibration-fragment": True},  # grounded in observed task outcome
    judgments={"sensor calibration": ["calibration-fragment"]},
    feedback_id="task-cycle-42",
    strength=0.1,
    k=5,
)
print(result.comparison.mean_reciprocal_rank_delta)
print(result.comparison.improved_queries, result.comparison.regressed_queries)
```

A feedback target outside the query's retrieved results is rejected before mutation. Reusing a feedback ID remains idempotent; rerunning an experiment after the first application can therefore correctly report no additional change.


## Association consolidation from recurring co-activation

The fragment archive can now accumulate evidence that two or more fragments repeatedly appear in the same observed episode. Call `observe_coactivation()` with the fragment IDs and a unique operation ID for that episode. Each unordered pair receives at most one observation per operation; by default, a bidirectional association is created after the pair co-occurs twice. The threshold is configurable with `min_observations`.

```python
result = memory.observe_coactivation(
    ["sensor-calibration", "maintenance-procedure"],
    context="maintenance",
    operation_id="episode-2026-0042",
    min_observations=2,
)
print(result["pairs"])
evidence = memory.association_evidence("sensor-calibration", "maintenance-procedure")
```

The observation ledger is persistent and idempotent. Replaying the same operation and payload does not increase evidence; reusing its ID for different input is rejected. `association_evidence()` exposes the count, contexts and last observation timestamp for inspection. Once the threshold is reached, links participate in the existing one-hop associative recall.

This is deliberately conservative: co-occurrence is evidence of a repeated relationship, not proof of causation or semantic equivalence. Fragment content, provenance, confidence, global importance and pinning are unchanged, and fragments are never merged or deleted. Use stable operation IDs tied to real episodes to avoid counting retries as new experiences.


Association influence now reflects the amount of accumulated evidence: repeated co-activation increases strength with diminishing returns. In associative recall, evidence-backed links scale the related-fragment contribution, while manually created links without a co-activation ledger retain their previous behavior. This prevents a single observed co-occurrence from automatically carrying the same influence as a repeatedly observed relation.

An optional `association_decay_half_life_seconds` constructor setting makes old evidence contribute less over time. For simulations, `association_strength(fragment_id, related_id, as_of=..., half_life_seconds=...)` exposes the effective value. Decay changes ranking influence only: it never removes the link, decreases the historical observation count, or deletes evidence. The default is disabled for temporal decay to preserve predictable behavior.

Association evidence is also tracked independently by normalized context. Passing `context="maintenance"` to `association_strength()` evaluates only co-activations observed in that context; an evidence-backed association with no observations in the requested context contributes zero associative strength for that context. When `recall(..., context=...)` is used, related-fragment ranking uses this context-specific strength. Calls without a context continue to use the aggregate evidence. This lets the same pair of fragments be strongly connected in one activity and weakly connected in another without deleting either the relation or its global history.

Outcome-based association learning is available through `apply_association_feedback_batch({("fragment-a", "fragment-b"): True}, context="maintenance", operation_id="...", strength=0.1)`. Positive feedback raises a pair's contextual utility score, while negative feedback lowers it; the neutral score is 0.5. That score scales only the association's influence in the named context, is clamped to valid bounds, and is stored independently from co-activation counts and fragment importance. Batches are transactional and idempotent: retrying the same operation does not apply learning twice, and reusing an operation ID with a different payload is rejected. Feedback requires an existing evidence-backed association and does not fabricate links.
