# MNN F5 — Contextual Retrieval and Contradiction Evidence

## Purpose

The fragment archive supports lexical retrieval and explicit one-hop
associations. This step adds:

1. **Context expansion:** callers can map query terms to known alternate
   phrases. Retrieval checks the original query and explicit expansions, then
   deduplicates fragment IDs. Existing links can contribute related context.
2. **Structured conflict detection:** fragments may carry a metadata claim
   object with subject, predicate, and value. Two claims with the same subject
   and predicate but different normalized values are reported with both
   fragment IDs and source URIs.

## Claim format

    metadata={
        "claim": {
            "subject": "valve A",
            "predicate": "state",
            "value": "open",
        }
    }

A later observation with the same subject/predicate and value "closed" yields
a conflict record referencing both sources. The system does not silently pick
one as true. A downstream policy must assess recency, confidence, provenance,
and context before deciding what to believe.

## Limits

- Aliases are supplied explicitly. This is not automatic synonym learning,
  vector embeddings, or proof of semantic understanding.
- Conflict detection compares structured claims only. It does not infer
  arbitrary natural-language contradictions.
- Different values are flagged for review; they may reflect changing states,
  different contexts, measurement error, or genuine disagreement.
- These capabilities are deterministic memory tools, not evidence of
  consciousness or general reasoning.

## Validation

tests/test_memory_reasoning.py covers alias recovery, related-context
deduplication, evidence provenance, equivalent structured values, rejection
of unstructured contradiction guesses, and input validation.
