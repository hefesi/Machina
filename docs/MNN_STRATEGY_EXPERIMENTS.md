# MNN Strategy Experiment Log and Evaluation

`MNNStrategyExperimentLog` stores a proposal and its observed outcome as
separate append-only `strategy-experiment` fragments in `FragmentMemory`.
`MNNStrategyExperimentEvaluator` aggregates repeated trials from an explicit
campaign and reports a conservative comparison of observed reward means.

## Run repeated trials

Use one `campaign_id` across independent experiment IDs. To compare actions,
record trials for both the current/baseline action and the candidate action.
Every proposal's `planned_action` must match the action actually tested:

```python
from machina import MNNStrategyExperimentLog, MNNStrategyExperimentEvaluator

log = MNNStrategyExperimentLog(memory, actions=("baseline", "candidate"))
review = {"status": "candidate", "candidate_action": "candidate"}
for i, (action, reward) in enumerate([
    ("baseline", 0.3), ("baseline", 0.4),
    ("candidate", 0.8), ("candidate", 0.9),
]):
    trial_id = f"workload-a-{i}"
    log.begin(
        trial_id,
        hypothesis="candidate improves reward on workload A",
        context="workload A",
        current_action="baseline",
        planned_action=action,
        review=review,
        campaign_id="workload-a-comparison",
    )
    # The caller/environment runs the action and supplies its observed reward.
    log.complete(
        trial_id, tested_action=action, observed_reward=reward,
        decision="collect_more_data",
    )

evaluator = MNNStrategyExperimentEvaluator(
    memory, actions=("baseline", "candidate"),
    min_samples_per_action=3,
    min_reward_margin=0.1,
    noise_guard_multiplier=1.0,
)
result = evaluator.evaluate("workload-a-comparison")
```

In this example, the evaluator returns `inconclusive` because only two samples
per action were supplied and the configured minimum is three. Increase the
number of independent trials before drawing a conclusion.

## Interpretation

- `candidate_better`: the candidate's observed mean exceeds the current action's
  mean by at least `min_reward_margin` and the observed difference is larger
  than the configured noise guard.
- `current_better`: the current action's observed mean exceeds the candidate's
  mean by the same margin and noise guard.
- `inconclusive`: sample counts are insufficient, the mean difference is too
  small, or observed variability is too large relative to the difference.
- `abstain`: no proposals exist, action roles cannot be established consistently, or a campaign mixes contexts. Keep each campaign limited to one comparable context.
- The result includes per-action counts, means, sample variances, sample standard
  deviations, estimated standard error of the mean difference, and outcome-fragment
  IDs for audit. At least two samples per action are required to estimate variability.
- `noise_guard_multiplier` (default `1.0`) requires the absolute mean difference
  to exceed that multiplier times the estimated standard error
  `sqrt(var_current / n_current + var_candidate / n_candidate)`. Set it to `0`
  to disable this additional guard while retaining the minimum reward margin.
- The evaluator is read-only. It does not execute trials, change policy, or
  automatically adopt a candidate.
- The variance guard is a conservative heuristic, **not** a confidence interval,
  statistical significance test, or calibrated probability. It does not establish
  causality and cannot compensate for biased or unsafe experimental design. Trials
  should be comparable and controlled by the caller.

## Review performance over time

Use `evaluate_over_time` to compare the candidate's advantage in an early
window with its advantage in a late window. Outcomes are ordered by their
persisted creation timestamps; each action needs at least two non-overlapping
windows of observations:

```python
trend = evaluator.evaluate_over_time(
    "workload-a-comparison",
    window_size=3,
)
```

- `advantage_persisted`: the candidate's mean-reward advantage meets the
  configured margin in both windows.
- `advantage_emerged`: the advantage meets the margin only in the late window.
- `advantage_reversed`: an early advantage later reverses beyond the margin.
- `no_clear_change`: the windows do not support one of those patterns.
- `inconclusive`: insufficient observations; `abstain`: ambiguous context or
  action roles.

The result includes early and late means by action, advantage differences,
change in advantage, and evidence fragment IDs. This is a descriptive temporal
comparison, not a formal drift detector, significance test, or causal estimate.
Use comparable contexts and deliberately designed trials; time ordering alone
does not isolate environmental changes from other factors.

## Log guarantees

- Proposal and outcome are separate immutable records. Identical retries are
  idempotent; reusing an event ID with different data is rejected.
- Completion requires a persisted proposal and the tested action must match its
  planned action.
- Supported audit decisions are `keep_current`, `validate_candidate_further`,
  and `collect_more_data`; these labels do not modify policy.
- If `campaign_id` is omitted, the trial is isolated under its own experiment ID.
