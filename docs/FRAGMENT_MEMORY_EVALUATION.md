# F4 — Fragment priority, archive retention, and retrieval

## Purpose

This experiment separates three states that must not be conflated:

- **Low active priority:** a fragment falls outside a bounded active view.
- **Retrieval miss:** a query returns no lexical matches even though the record
  remains in the archive and can be directly loaded by ID.
- **Deletion:** the record is absent from the persistent archive.

It also tests whether explicit reinforcement and pinning can make a stored
fragment active again without creating a duplicate or deleting other records.

## Run

```bash
python -m benchmarks.fragment_memory_retrieval
python -m unittest tests.test_fragment_memory_evaluation -v
python -m unittest discover -s tests -v
```

The benchmark uses a fixed 30-day timestamp offset in a SQLite fixture rather
than sleeping, so priority decay is deterministic. It uses the existing
`FragmentMemory` API for adding, ranking, archive listing, lexical recall,
direct lookup, and reinforcement. The timestamp update is test-fixture setup,
not a new production API.

## Expected observations

1. The aged rule falls outside the two-entry active view, which contains the pinned critical item and the recent note.
2. The aged rule remains in the archive; the archive count stays at three.
3. A deliberately unrelated lexical query returns no matches, but direct
   lookup still retrieves the stored rule.
4. Reinforcing and pinning the rule makes it the top active fragment without
   changing the archive membership.

## Limits

The archive is persistent SQLite storage; the active view is only a ranked
projection. A lexical miss does not establish why a human or semantic agent
would fail to recall something. This benchmark distinguishes storage state
from one retrieval method, but does not yet test embedding retrieval, semantic
equivalence, consolidation policies, or consciousness.
