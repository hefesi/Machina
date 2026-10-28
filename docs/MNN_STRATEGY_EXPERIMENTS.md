# MNN Strategy Experiment Log

`MNNStrategyExperimentLog` stores a proposed strategy review and its observed
outcome as separate, append-only `strategy-experiment` fragments in
`FragmentMemory`.

## Example

```python
from machina import MNNStrategyExperimentLog

log = MNNStrategyExperimentLog(memory, actions=("baseline", "candidate"))
proposal = log.begin(
    "trial-2026-001",
    hypothesis="The candidate action improves reward in workload A",
    context="workload A",
    current_action="baseline",
    planned_action="candidate",
    review=strategy_review,
)
# The caller/environment—not the log—runs the controlled trial and measures reward.
outcome = log.complete(
    "trial-2026-001",
    tested_action="candidate",
    observed_reward=0.7,
    decision="validate_candidate_further",
    observation="One observation; repeat before concluding.",
)
```

## Guarantees and limits

- Proposal and outcome are separate immutable records; retrying an identical event
  is idempotent, while reusing an event ID with different data is rejected.
- The log preserves review evidence IDs and references the proposal from its outcome.
- Completion requires a stored proposal and the tested action must match the planned action.
- Supported decisions are `keep_current`, `validate_candidate_further`, and
  `collect_more_data`. These are audit labels only.
- `policy_changed` is always false. The log does not execute actions, adopt a
  candidate, alter learner parameters, or establish causality.
- Reward values are observations from the caller; the module does not validate
  experimental controls, sample size, or environmental safety.
