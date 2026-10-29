# MNN Reward Drift Detection

## Purpose

`MNNRewardDriftDetector` checks whether observed rewards for the same action and a lexically matching context have shifted between two adjacent decision windows. It can surface a possible change in operating conditions to a caller, without claiming to identify the cause.

## Decision rule

- Read only `action-outcome` fragments with valid non-negative integer `decision` metadata.
- Select the latest two windows containing `decisions_per_window` distinct decision indices.
- Match context using token overlap, defaulting to 60% of query tokens.
- Compare confidence- and context-overlap-weighted mean rewards for each action in each window.
- Report `detected` if any action's absolute reward change meets `min_reward_shift`; report `stable` when comparable samples exist but no change reaches the threshold; otherwise `abstain`.

The detector does not mutate the archive, change policy parameters, or execute actions. The caller decides whether to reduce confidence, request more observations, or evaluate alternatives. This is a descriptive detector, not a calibrated statistical change-point test: overlapping windows, noisy rewards, biased exploration, and context labels can mislead it.

## Example

```python
from machina import MNNRewardDriftDetector

detector = MNNRewardDriftDetector(
    memory,
    decisions_per_window=10,
    min_samples_per_action_window=3,
    min_reward_shift=0.25,
)
report = detector.detect("stable workload")
if report["status"] == "detected":
    # Review evidence and gather validation before changing policy.
    print(report["shifted_actions"])
```

Each comparison includes prior/recent means, sample counts, decision windows, and fragment IDs for audit. History remains intact.


## Agent integration

The agent can optionally review drift during a decision by receiving an `MNNRewardDriftDetector` bound to the same `FragmentMemory` instance and calling:

```python
decision = agent.decide(
    context="stable workload",
    review_reward_drift=True,
)
report = decision["reward_drift_review"]
if report and report["status"] == "detected":
    # Review evidence and gather another outcome before changing strategy.
    ...
```

This integration is deliberately advisory. A detected shift or insufficient history sets `request_experience`; the detector does not select an action, override the learner, or execute a trial. Drift review is opt-in and validates its context before the learner's decision counter advances.
