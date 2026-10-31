# Curiosity Investigation Memory

## Purpose

`CuriosityInvestigationStore` gives knowledge-gap exploration a durable,
auditable lifecycle. It records what the system intended to investigate,
why the goal was selected, the hypothesis being tested, caller-supplied
evidence references and findings, the conclusion, and unresolved questions.

The store is SQLite-backed and survives process restarts.

## Lifecycle

1. `start_investigation()` opens a uniquely identified investigation with a
   gap property, question, hypothesis, selection rationale, cycle, and goal.
2. `record_evidence()` appends a finding linked to a non-empty external
   evidence reference. Evidence is kept separate from the hypothesis and
   cannot be edited or duplicated within the same investigation.
3. `close_investigation()` records one of four outcomes:
   `answered`, `partially_answered`, `unanswered`, or `abandoned`.
   Every closure includes a summary and an explicit list of remaining
   unknowns, including an empty list when none remain.
4. `history()` and `get_investigation()` reconstruct the durable record,
   including evidence and the cycle in which it was closed.

An investigation cannot be reopened, closed twice, or receive evidence after
closure. Equivalent whitespace/case-normalized questions for the same gap
cannot be open simultaneously. Database uniqueness constraints protect these
invariants across concurrent store instances.

## Avoiding repeated questions

`SelfModelLearningBridge.propose_curiosity_goals()` accepts an optional
`investigation_store`. When supplied, it suppresses proposals whose normalized
question for that property already appears in the investigation history.
The result exposes these entries under `suppressed` with a reason.
`allow_repeat=True` is an explicit override for a deliberate retry.

This is exact normalized text matching, not semantic deduplication. Different
wordings may still describe the same underlying question.

## Epistemic and safety boundaries

- Questions, hypotheses, selection reasons, findings, and evidence references
  are supplied by the integrating caller; the store does not browse or verify
  external sources.
- An evidence reference is an audit pointer, not proof that the referenced
  material is reliable or supports the finding.
- Findings are recorded separately from hypotheses and final summaries so
  later review can distinguish observation from interpretation.
- The ledger does not infer that a hypothesis is true, update the self-model,
  execute research, grant tool permissions, or authorize external actions.
- Persistence and continuity of an investigation are engineering properties;
  they are not evidence of subjective curiosity, consciousness, or free will.
