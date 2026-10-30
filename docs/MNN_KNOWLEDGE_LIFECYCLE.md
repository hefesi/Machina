# MNN Knowledge Lifecycle v0.1

## Purpose

`MNNKnowledgeLifecycle` coordinates the existing evidence-grounded concept builder
and concept reviewer into one inspectable maintenance pass. It does not add a
new semantic inference engine.

## Pipeline

1. Review persisted concepts against the current evidence archive.
2. Discover recurring tag-based concept hypotheses.
3. Optionally materialize refreshed concept snapshots.
4. Review the archive again so callers can inspect current, stale, conflicted,
   and unverified concepts.
5. Optionally persist idempotent review audit fragments.

## Usage

```python
from machina import FragmentMemory, MNNKnowledgeLifecycle

with FragmentMemory("memory.sqlite3") as memory:
    lifecycle = MNNKnowledgeLifecycle(memory, min_support=2)
    result = lifecycle.run()
    print(len(result.hypotheses))
    print(result.conflicted_count)
```

Use `run(refresh=False, persist_audit=False)` for an observational pass that
does not write to memory. The two flags can also be controlled independently.

## Safety and semantics

- Source evidence fragments are never rewritten or deleted.
- Previous concept snapshots remain archived when evidence changes.
- Discovery uses explicit shared tags; it is not open-ended language understanding.
- Contradictions come from explicit evidence polarity or persisted explicit
  concept relations, not from wording similarity.
- Confidence is a ranking heuristic inherited from the builder, not a calibrated
  probability.
- Repeated runs over an unchanged archive are idempotent for concept and audit IDs.
- The coordinator exposes intermediate results instead of collapsing the cycle
  into an opaque score.

## Validation target

Tests cover discovery and materialization, idempotent repeated runs, read-only
observation mode, conflict surfacing, and input validation. A later integration
step should connect this lifecycle to the durable `VirtualBrain` cycle only
after defining transaction and recovery semantics across `EventStore` and
`FragmentMemory`.
