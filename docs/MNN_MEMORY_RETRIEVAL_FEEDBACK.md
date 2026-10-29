# MNN memory retrieval feedback v0.1

## Purpose

MNNMemoryRetrievalFeedback provides an explicit feedback loop between a retrieval result and the existing SQLite-backed FragmentMemory.

- Positive usefulness feedback raises a fragment's retrieval importance.
- Negative usefulness feedback lowers importance, but does not claim the content is false.
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

## Important distinction

Usefulness is task-relative. A memory can be unhelpful for one query and still be true or important in another context. Callers should send feedback only when a retrieval outcome has been observed; do not treat lack of retrieval or low lexical overlap as proof that a memory should be forgotten. Pinned records remain pinned, and this component never deletes archived fragments.

## Validation

Unit tests cover positive/negative feedback, persistence across reopen, bounds, invalid inputs, missing fragment IDs, mixed batch updates, prevalidation, and idempotent retries using `feedback_id`. The feedback ledger and importance updates are committed in one SQLite transaction. Integration tests verify that feedback can change subsequent lexical recall ranking. Run with:
python -m unittest tests.test_mnn_memory_retrieval_feedback
