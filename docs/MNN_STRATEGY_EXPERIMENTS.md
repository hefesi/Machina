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
    min_samples_per_action=3, min_reward_margin=0.1,
)
result = evaluator.evaluate("workload-a-comparison")
```

In this example, the evaluator returns `inconclusive` because only two samples
per action were supplied and the configured minimum is three. Increase the
number of independent trials before drawing a conclusion.

## Interpretation

- `candidate_better`: the candidate's observed mean exceeds the current action's
  mean by at least `min_reward_margin`, with the required samples for both.
- `current_better`: the current action's observed mean exceeds the candidate's
  mean by the same threshold.
- `inconclusive`: sample counts are insufficient or the difference is too small.
- `abstain`: no proposals exist or action roles cannot be established consistently.
- The result includes per-action counts, means, and outcome-fragment IDs for audit.
- The evaluator is read-only. It does not execute trials, change policy, or
  automatically adopt a candidate.
- This is a simple empirical-mean heuristic, not a statistical significance test.
  It does not establish causality and cannot compensate for biased or unsafe
  experimental design. Trials should be comparable and controlled by the caller.

## Log guarantees

- Proposal and outcome are separate immutable records. Identical retries are
  idempotent; reusing an event ID with different data is rejected.
- Completion requires a persisted proposal and the tested action must match its
  planned action.
- Supported audit decisions are `keep_current`, `validate_candidate_further`,
  and `collect_more_data`; these labels do not modify policy.
- If `campaign_id` is omitted, the trial is isolated under its own experiment ID.
