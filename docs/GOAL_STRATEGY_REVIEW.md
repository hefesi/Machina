# Longitudinal Goal Strategy Review

`SelfModelLearningBridge.review_goal_strategy()` compares two consecutive,
non-overlapping windows of evaluator-supplied outcomes for one goal type.

## Contract

- Requires at least `2 * window_size` observations; otherwise it returns
  `insufficient_history` without mutating the self-model.
- Compares the mean of the most recent window with the immediately preceding
  window.
- Classifies a change as `improving`, `deteriorating`, or
  `no_material_change_detected` using the caller's `minimum_change` threshold.
- Stores an `inferred` descriptive belief with references to the underlying
  outcome records. Repeated review over the same evidence window is idempotent.
- A later non-overlapping window creates a belief revision, preserving the
  previous assessment and marking whether the assessment label changed.

## Interpretation and safety boundary

This is a temporal comparison, not a causal experiment. It does not control
for task difficulty, environment changes, evaluator drift, selection effects,
or other confounders. A deteriorating assessment recommends that a strategy
be reviewed; it does not modify the strategy, select a different goal, change
autonomy scores, execute actions, or grant permissions. An improving
assessment recommends retaining and validating the strategy, not assuming
general success.

The confidence field is an evidence-volume support heuristic, capped at 0.75.
It is not a probability that the assessment is true and is not a statistical
confidence interval. Causal claims remain restricted to the separate,
explicitly gated causal-experiment workflow.
