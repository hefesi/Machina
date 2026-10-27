# MNN Evidence-Grounded Concepts

## Purpose

`MNNConceptBuilder` is the next layer after persistent fragment memory and memory consolidation. It identifies recurring explicit tags across source fragments and creates inspectable concept hypotheses with links to their evidence. It is deliberately conservative: shared tags are a weak pattern signal, not proof that the underlying statements are semantically equivalent.

## Example

```python
from machina.fragment_memory import FragmentMemory
from machina.mnn_concepts import MNNConceptBuilder

with FragmentMemory("machina-memory.sqlite3") as memory:
    memory.add(
        "The system overheats under heavy load",
        source_uri="experiment://run-1",
        tags=["temperature", "heavy-load"],
        confidence=0.8,
        metadata={"polarity": "supports"},
    )
    memory.add(
        "Temperature rose during a second load test",
        source_uri="experiment://run-2",
        tags=["temperature", "heavy-load"],
        confidence=0.75,
        metadata={"polarity": "supports"},
    )
    builder = MNNConceptBuilder(memory, min_support=2)
    hypotheses = builder.discover()
    derived_records = builder.consolidate()
```

## Current algorithm

1. Read archived `fact` and `experience` records; ignore previously derived `concept` records to prevent recursive self-confirmation.
2. Group evidence by normalized explicit tags. A tag must occur in at least `min_support` source records.
3. Report each source ID and classify evidence conservatively:
   - `supported`: at least `min_support` records explicitly declare `metadata["polarity"] = "supports"` and none explicitly contradicts.
   - `conflicted`: both `supports` and `contradicts` are present for the same tag.
   - `insufficient`: the evidence count exists, but there are not enough explicitly supporting records to call it supported.
   - Missing/unknown polarity is not treated as support.
4. Estimate a bounded confidence-ranking heuristic from mean source confidence and a saturating support factor. This is **not** a calibrated probability.
5. Optionally materialize the hypothesis as a `kind="concept"` fragment with evidence IDs in both `related_ids` and metadata. The deterministic ID makes repeating materialization for the same evidence idempotent.

## Provenance and change handling

Source records are never merged, rewritten, or deleted. Derived concepts keep their evidence IDs and polarity breakdown. If new evidence arrives, call `discover()` again; a changed evidence set produces a new derived record ID, preserving the old concept as a historical snapshot. This means old concepts can become stale, so consumers should compare a concept's recorded evidence IDs with current discovery results before treating it as current.

`polarity` must be provided explicitly by the environment or an upstream evaluator; this module does not infer whether arbitrary natural-language statements contradict one another. A tag is only as meaningful as the process that assigned it.

## Tests and benchmark

```bash
python -m unittest tests.test_mnn_concepts -v
python benchmarks/mnn_concepts.py
```

The benchmark demonstrates repeated tags and an explicitly marked counter-observation. It tests traceability and conflict bookkeeping, not semantic understanding, causal discovery, consciousness, or general intelligence.

## Next work

A useful next step is a revision loop: compare newly observed evidence with existing concept records, mark concepts as current/stale/conflicted, and measure whether using concepts improves downstream task reward over a no-concept baseline. That loop should keep source evidence immutable and make confidence calibration an empirical question.
