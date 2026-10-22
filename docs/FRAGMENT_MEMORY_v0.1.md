# Machina — Fragment Memory v0.1

## Design principle

Memory is not a flat list and forgetting must not equal deletion. Machina keeps
small information fragments with provenance and associations. An active view
ranks a bounded subset for current use, while the persistent archive retains
fragments whose priority has fallen.

## Fragment fields

Each fragment stores content, kind, source URI, importance, confidence, creation
time, last access, access count, tags, associations, metadata, and a pin flag.
Associations are explicit bidirectional links; linking does not merge or delete
either fragment.

## Priority policy (initial baseline)

The active-view score is:

`score = importance × exp(-decay_per_day × age_days) + usage_bonus + context_bonus`

The usage bonus is bounded and increases with access count. A matching tag adds
a context bonus. Pinned fragments receive a minimum score of 0.95. Scores are
bounded to [0, 1] and ties are resolved deterministically.

This is a tunable engineering baseline, not a model of human memory. In
particular, repeated access is not proof that a fact is true, and low priority
does not mean low truth or permanent deletion. Confidence is stored separately
from importance. A later version should include dependency centrality, expiry
and contradiction handling, semantic retrieval, and measured calibration.

## Query retrieval

`recall(query, limit=5, include_related=True)` ranks fragments by lexical token overlap, importance, confidence, and tag matches. It can also include one-hop linked fragments as contextual candidates even when their wording does not match the query. This is a deterministic lexical baseline, not semantic retrieval; embeddings and semantic evaluation remain future work. Retrieval does not mutate or delete fragment records.

## Non-destructive forgetting

- `active(limit=N)` provides a bounded, priority-ranked view.
- `archive()` retrieves stored fragments regardless of active priority.
- No decay or active-view operation deletes a fragment.
- Important or hard-to-reconstruct fragments can be pinned explicitly.
- The source URI remains attached for auditing and future verification.

## Usage

```python
from machina.fragment_memory import FragmentMemory

with FragmentMemory("data/fragments.sqlite3") as memory:
    fact = memory.add(
        "A critical design decision",
        source_uri="project://architecture",
        importance=0.95,
        confidence=0.9,
        tags=["architecture"],
        pinned=True,
    )
    current = memory.active(limit=20, query_tags=["architecture"])
```

## Scope

This is a memory substrate, not autonomous knowledge acquisition or reasoning.
It does not browse the web, infer semantic similarity, or decide truth. The
module is deliberately separate from existing MNN weights and VirtualBrain
cycles until its behavior is tested and integrated explicitly.

## Verification

Run from the repository root: `python -m unittest discover -s tests -v`.
