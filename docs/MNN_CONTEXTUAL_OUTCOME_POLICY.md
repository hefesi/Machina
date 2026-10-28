# MNN Contextual Outcome Policy

## Purpose

`MNNContextualOutcomePolicy` adds a conservative, auditable bridge between stored action outcomes and contextual recommendations. It examines the persistent `FragmentMemory` archive and groups observed rewards by action when the stored context has sufficient lexical overlap with the requested context.

## Decision rule

A recommendation is returned only when:

1. Every configured action has at least `min_samples_per_action` comparable outcome records.
2. The estimated reward for the leading action exceeds the runner-up by at least `min_reward_margin`.
3. Evidence meets the configured `min_context_overlap` threshold.

Estimates are confidence- and overlap-weighted reward averages. By default, at least 60% of query context tokens must match a stored context; this helps avoid mixing examples such as "stable workload" and "risky workload" merely because they share the word "workload". The result includes sample counts and fragment IDs for audit. If evidence is missing or the estimates are close, the policy returns `status="abstain"` with a reason.

## Example

```python
policy = MNNContextualOutcomePolicy(
    memory,
    ["continue", "pause"],
    min_samples_per_action=3,
    min_reward_margin=0.2,
)
decision = policy.recommend("stable workload")
if decision["status"] == "recommended":
    action = decision["action"]
else:
    # Ask the environment for another observed trial or use a safe fallback.
    action = None
```

Import it from `machina` or `machina.mnn_contextual_outcome_policy`.

## Agent integration

Pass a policy whose configured actions exactly match the agent learner's action order, then explicitly enable it for a decision:

```python
policy = MNNContextualOutcomePolicy(memory, learner.actions)
agent = MNNLearningAgent(learner, memory, outcome_policy=policy)
decision = agent.decide(context="stable workload", use_outcome_policy=True)
# Resolve only after the environment returns a real reward.
agent.resolve(observed_reward, context="stable workload")
```

The agent prioritizes an available concept recommendation, then an outcome-policy recommendation, then optional legacy memory guidance, and finally its learner fallback. If the outcome policy abstains, the agent requests another experience and uses its fallback. The action is not executed automatically. The pending action source is preserved by agent snapshots; pass the same policy when restoring if future policy-guided decisions are needed.

## Boundaries and limitations

- This is an empirical association, not causal inference, semantic comprehension, or a guarantee of future reward.
- Context matching is lexical, not embedding-based; it requires meaningful shared words.
- The policy does not execute actions, alter memory, or train the global action learner.
- It requires minimum comparable samples for **all** configured actions to avoid treating an untested alternative as inferior.
- Reward averages can be distorted by changing environments, biased exploration, confounders, and non-stationary reward distributions. A later iteration should add time windows, uncertainty estimates, and online calibration before this policy is used in safety-critical settings.
- This mechanism does not establish consciousness or free will.
