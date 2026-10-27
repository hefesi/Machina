# MNN Concept Revision and Review

## Purpose

`MNNConceptReviewer` checks whether a persisted concept still matches the current evidence archive. It is a revision and provenance layer on top of `MNNConceptBuilder`, not a natural-language contradiction detector.

## States

- `current`: the concept's recorded evidence IDs exactly match the current hypothesis and no explicit polarity conflict exists.
- `stale`: the evidence set changed, or no current hypothesis meets the minimum support threshold. A stale concept remains available as a historical snapshot.
- `conflicted`: the current evidence for the concept key contains both explicitly supporting and contradicting records.
- `unverified`: the concept lacks valid provenance metadata, so the reviewer cannot responsibly establish freshness.

These are derived review states. The reviewer never edits or deletes source fragments or old concepts. Call `review()` whenever new evidence is added. Call `refresh()` to materialize the current hypothesis as a new concept snapshot; previous snapshots remain in the archive.

## Usage

```python
from machina.fragment_memory import FragmentMemory
from machina.mnn_concept_review import MNNConceptReviewer

with FragmentMemory("machina-memory.sqlite3") as memory:
    reviewer = MNNConceptReviewer(memory, min_support=2)
    for item in reviewer.review():
        print(item.concept.id, item.state, item.added_evidence_ids, item.explanation)

    # Optional: persist an idempotent audit record for each review state.
    reviewer.persist_review_log()

    # After new evidence has been added, make fresh concept snapshots.
    reviewer.refresh()
```

`persist_review_log()` stores records with `kind="concept_review"`; they are audit entries, not evidence and are excluded from default concept discovery. The same concept/state/evidence snapshot produces the same log ID, so repeating a review does not duplicate identical log records. A changed state or evidence set creates a new audit record.

## Validation

```bash
python -m unittest tests.test_mnn_concept_review -v
```

Tests cover matching evidence, new evidence making an old snapshot stale, explicit contradiction, preservation of old records, idempotent review logs, and concepts without provenance.

## Limits

The reviewer relies on tags and explicit `metadata["polarity"]` supplied by the environment or an upstream evaluator. It does not infer contradiction from arbitrary text. `current` means only that the evidence ID set matches the current heuristic hypothesis; it is not a claim that the concept is objectively true. Review should be treated as bookkeeping and uncertainty management, not proof of understanding.
