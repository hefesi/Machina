# MNN priority-weighted fragment memory (experimental)

This module implements a small, deterministic memory policy for Machina. It
stores information as independently addressable fragments rather than a single
unbounded transcript.

## Model

Each fragment has content, importance, retained strength, timestamps, access
count, tags, and an optional protection flag. Retrieval ranks lexical overlap
with a query alongside importance and strength. Access reinforces the retrieved
fragment slightly. Decay reduces retained strength, with high-importance
fragments decaying more slowly. Protected fragments do not decay and are not
eligible for pruning or capacity eviction.

The priority score is:

`priority = 0.7 * importance + 0.3 * strength`

Retrieval score:

`score = 0.65 * lexical_overlap + 0.25 * importance + 0.10 * strength`

These are tunable engineering heuristics, not claims about the exact biology of
human memory. Lexical overlap is intentionally simple; semantic retrieval,
conflict resolution, provenance, and consolidation remain future work.

## Safety and persistence

- Decay never deletes a fragment automatically.
- Pruning is explicit and deterministic.
- Protected and critical (importance >= 0.95) fragments are retained.
- A full store raises `OverflowError` if every candidate is protected/critical.
- `snapshot()` and `from_snapshot()` support JSON-compatible persistence.

## Quick start

```python
from machina.mnn_memory import MemoryFragment, PriorityMemory

memory = PriorityMemory(capacity=500)
memory.remember(MemoryFragment(
    id="mnn-plasticity",
    content="Reward-modulated plasticity updates connection weights.",
    importance=0.9,
    tags=("MNN", "learning"),
))
relevant = memory.retrieve("how does MNN learn?", limit=3)
memory.decay(rate=0.01, steps=1)
saved_state = memory.snapshot()
```

Run tests from the repository root:

```bash
python -m unittest tests.test_mnn_memory -v
```

## Validation boundary

Passing tests validates the implemented mechanics and deterministic policy only.
It does not establish human-like memory, semantic understanding, consciousness,
or general intelligence.
