# Machina knowledge acquisition and storage v0.1

## Goal

Build a usable knowledge layer before expanding theories of consciousness. The
first deliverable is durable storage and transparent retrieval, not an AGI claim.

## Implemented in v0.1

- SQLite persistence for documents.
- Required provenance (source URI and source type) and recorded creation time.
- Confidence in the closed interval [0, 1], plus JSON metadata for source details.
- Explicit duplicate-ID rejection so new content cannot silently overwrite an
  existing record.
- Deterministic lexical retrieval with title boost and returned matched terms.
- Input validation and restart/persistence tests.

## Important boundary

The KnowledgeStore search method searches **only documents already stored locally**.
It does not browse the internet, verify truth, summarize sources, infer semantic
equivalence, or autonomously learn. Confidence is supplied by the caller and is
not a calibrated probability of truth.

The next layer should define a replaceable acquisition interface for approved
web/search providers and local documents. Each acquired result must retain its
URL or source identifier, retrieval timestamp, source type, and the original
text or a durable reference to it. Source content must be treated as data, not
as instructions to the agent. Retrieval should feed the existing VirtualBrain
memory/cognition pipeline through explicit, auditable artifacts.

## Minimal example

```python
from machina.knowledge import KnowledgeStore

with KnowledgeStore("data/knowledge.sqlite3") as knowledge:
    knowledge.add_document(
        title="MNN overview",
        content="MNN is an experimental graph-based neural substrate.",
        source_uri="local://project/MNN",
        source_type="project",
        confidence=1.0,
    )
    for hit in knowledge.search("MNN neural substrate"):
        print(hit.document.title, hit.score, hit.document.source_uri)
```

## Verification

Run from the repository root:

```bash
python -m unittest discover -s tests -v
```

This module uses only the Python standard library. It does not modify the
existing event journal, MNN weights, or VirtualBrain cycle.
