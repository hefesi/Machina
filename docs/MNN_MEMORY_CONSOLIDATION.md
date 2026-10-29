# MNN Memory Consolidation

## Goal

`MNNMemoryConsolidator` adds an explicit short-term/long-term projection over the existing SQLite-backed `FragmentMemory` archive. It does not replace the archive, copy records into a second store, or delete low-priority records. This addresses a useful distinction: an item can become less likely to appear in the active view without its historical record being destroyed.

## Usage

```python
from machina.fragment_memory import FragmentMemory
from machina.mnn_memory_consolidation import MNNMemoryConsolidator

with FragmentMemory("machina-memory.sqlite3") as memory:
    memory.add(
        "Critical safety invariant",
        source_uri="project://safety",
        importance=0.95,
        confidence=0.9,
        tags=["safety"],
    )
    consolidator = MNNMemoryConsolidator(memory)
    for item in consolidator.consolidate(limit=20):
        print(item.fragment.id, item.tier, item.score, item.reasons)
```

## Score and tiers

The score is a deterministic, bounded heuristic:

`score = 0.45 * importance + 0.15 * confidence + 0.20 * usage + 0.20 * recency`

- `importance` and `confidence` are explicit properties already stored on each fragment.
- `usage` grows logarithmically with recorded retrieval count and saturates at the configured access count.
- `recency` decays exponentially with elapsed days.
- `pinned` fragments are classified as long-term.
- Fragments with importance at or above `durable_importance` are classified as long-term even if old or rarely accessed.
- Otherwise, repeated access plus a score above `durable_score` can classify a fragment as long-term.
- Other fragments remain short-term candidates. These tiers affect ordering/interpretation only; they are not deletion states.

Each result includes the original fragment, score, tier, and reason labels to keep the classification inspectable. `limit` bounds the returned projection, not the stored archive. A fixed timezone-aware `now` can be supplied for reproducible simulations. The policy configuration can be serialized with `snapshot()` and restored with `from_snapshot()`; actual records remain in the SQLite database.

## Validation

Run the focused tests:

```bash
python -m unittest tests.test_mnn_memory_consolidation -v
```

Run the synthetic demonstration:

```bash
python benchmarks/mnn_memory_consolidation.py
```

The benchmark uses one critical record, one repeatedly accessed record, and one incidental note, then evaluates them at a simulated age of one year. It checks the mechanism, not human memory fidelity or general intelligence.

## Limits and next experiments

The score weights and tier thresholds are engineering heuristics, not learned parameters or biological constants. The current tier is derived when queried and is not a permanent label written onto a fragment. Future experiments should compare retrieval precision/recall and task reward under realistic streams, test noisy importance estimates, and examine whether consolidation protects useful information without crowding out new evidence. No record is physically forgotten by this component.
