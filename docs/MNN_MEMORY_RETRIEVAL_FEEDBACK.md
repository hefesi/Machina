# MNN memory retrieval feedback v0.1

## Purpose

MNNMemoryRetrievalFeedback provides an explicit feedback loop between a retrieval result and the existing SQLite-backed FragmentMemory.

- Positive usefulness feedback raises a fragment's retrieval importance.
- Negative usefulness feedback lowers importance, but does not claim the content is false.
- Content, provenance, confidence, associations, and pin state are left unchanged.
- Importance remains bounded to [0, 1] and is persisted by the existing memory store.
- The result object records the applied signal and before/after importance for caller-side logging.

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

Unit tests cover positive/negative feedback, persistence across reopen, bounds, invalid inputs, and missing fragment IDs. Run with:
python -m unittest tests.test_mnn_memory_retrieval_feedback
