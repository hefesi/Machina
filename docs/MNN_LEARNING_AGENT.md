# MNN Learning Agent: Action, Outcome, and Memory

The `MNNLearningAgent` coordinates three explicit steps:

1. `decide()` selects an action and records it as pending.
2. `resolve(reward, context=...)` updates the action-value learner from the observed reward.
3. The outcome is archived as a `MemoryFragment` with action, reward, prediction error, decision number, and optional context.

The agent enforces one unresolved action at a time. Its snapshot includes the learner and any in-flight action; the SQLite memory is stored independently and reopened through `FragmentMemory`.

## Minimal example

```python
from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent

with FragmentMemory("machina-experience.sqlite3") as memory:
    agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
    decision = agent.decide()
    # The environment executes decision["action"] and measures an outcome.
    result = agent.resolve(1.0, context="quiet morning")
    print(result["learning_update"], result["experience_id"])
    print(agent.recall("quiet morning"))
    print(agent.recommend_from_memory("quiet morning"))
```

## Contextual recall from experience

`recommend_from_memory(context)` is an explicit, read-only retrieval step. It:
- retrieves fragments using the existing lexical memory search;
- filters for recorded action outcomes whose saved context shares tokens with the query;
- estimates each action's reward using a context-overlap-weighted mean;
- returns the recommendation, per-action estimates, and evidence fragment IDs;
- returns `None` if no usable matching context exists;
- abstains when the two best observed action estimates differ by less than `min_reward_margin` (default `0.1`), rather than silently breaking an ambiguous tie by action order;
- reports evidence counts, estimated rewards, and the decision margin when it can recommend.

The margin is a heuristic in the reward scale, not a calibrated probability of correctness. A recommendation based on a single fragment can still be fragile; callers should inspect evidence counts or request stricter experiment-specific criteria.

By default, it does **not** change the learner's action values or override `decide()`. For controlled experiments, `decide(context=..., use_memory=True)` explicitly allows a valid memory recommendation to select the action for that decision. The return value includes `selection_source`, `memory_recommendation`, and `fallback_action`, making memory influence observable.

If memory cannot recommend (because there is no matching evidence or the evidence is ambiguous), the learner makes the fallback choice. The decision result marks `memory_status="no_recommendation"`, supplies a conservative `fallback_reason`, and sets `request_experience=True`. This is a signal to the calling environment to prioritize observing and recording the outcome; it does not automatically execute a trial or claim that new evidence already exists. Resolve the actual outcome with `resolve()`.

## Exploration versus exploitation

`MNNActionLearner.choose()` keeps the original deterministic scheduled policy when `epsilon` is omitted. For experiments, pass `epsilon` to select an epsilon-greedy policy:

```python
decision = agent.decide(exploration_epsilon=0.15)
# Execute decision["action"] in the environment, then report the observed reward.
agent.resolve(reward=measured_reward, context="current situation")
```

`epsilon=0` greedily chooses the highest predicted utility after every action has been tried once; `epsilon=1` explores uniformly at random after that initial coverage. Values between 0 and 1 trade off exploitation and exploration. The seeded draw is derived from `exploration_seed + decision_number`, so the action sequence is reproducible across JSON snapshot/restart. `exploration_seed` defaults to `0` and is persisted by the learner.

The decision output reports `exploration_policy` and `exploration_epsilon`. This policy is a simple epsilon-greedy baseline, not a calibrated uncertainty model. It explores randomly rather than estimating epistemic uncertainty, and reward quality must be measured in a controlled environment.

## Controlled benchmark

Run `python benchmarks/mnn_contextual_memory.py` to compare the context-free baseline with memory-assisted selection on a deterministic two-context task where the best action reverses between contexts. The benchmark seeds the same four experience records for each policy and reports reward total, accuracy, and how often memory selected the action. It is a small synthetic sanity check, not proof of generalization; results depend on lexical retrieval and supplied experience.

## Guarantees and limits

- Rejects overlapping decisions and invalid rewards.
- Records each resolved action outcome as an auditable memory fragment.
- Supports restoring an in-flight action from a JSON-compatible snapshot.
- Does not claim atomic transactions across the learner and SQLite. If memory persistence fails after a learner update, the caller should treat that as a partial failure and recover from its last durable snapshot.
- Retrieval is lexical, not semantic; token overlap can confuse related or ambiguous contexts.
- The action learner is a small contextual-free bandit, not a general planning or consciousness model.
