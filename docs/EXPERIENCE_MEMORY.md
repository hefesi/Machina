# Experience memory

`ExperienceMemoryStore` is the durable ledger for the agent's own intentions and evaluated outcomes.

## Lifecycle

1. Call `begin(...)` before attempting a goal. It stores the cycle, goal, strategy,
   intention, optional expected score, context reference and prediction reference.
2. After the attempt, an evaluator calls `record_outcome(...)` with a score in
   [0, 1], an evidence reference, evaluator identity and rationale.
3. `get(...)` compares expected and observed scores when an expectation exists.
4. `strategy_report(...)` aggregates only evaluated experiences and requires a
   minimum sample before comparing strategies.

Intent and outcome identifiers are idempotent. Reusing an identifier with conflicting
content is rejected. An experience receives at most one outcome; corrections should
be represented by a separate review/evaluation mechanism rather than rewriting history.

## Boundaries

- The store does not execute goals, inspect free text to decide success, or create evidence.
- Scores and evidence references are supplied by an evaluator and remain attributable to it.
- Strategy differences are observational, context-sensitive summaries, not causal effects.
- Reports are recommendations only. They do not mutate the self-model, autonomy policy,
  goals, permissions, or execution state.
- This ledger is complementary to `GoalOutcomeLearner`: the latter learns
  goal-type outcome probabilities; this store preserves the specific intention,
  strategy, prediction and evidence chain. Integrations should use a shared
  outcome identifier to avoid counting one evaluation twice.
- None of these mechanisms demonstrates phenomenal consciousness or metaphysical
  free will. They make memory, self-evaluation and strategy revision hypotheses
  inspectable and testable.

## Autobiographical review

`autobiographical_report(...)` reconstructs an ordered record of intentions,
including pending experiences, and detects repeated signed prediction-error
patterns grouped by exact caller-supplied goal and strategy labels. A minimum
number of evaluated episodes is required. The report can identify repeated
overestimation or underestimation of outcomes, but cannot infer why it happened.

This is a descriptive self-history, not a semantic autobiography: evaluator
notes are not mined for hidden meaning, and no emotions, motives, causal
explanations or subjective experience are inferred. The report does not update
the SelfModel, alter autonomy or execute a recommended strategy change.
