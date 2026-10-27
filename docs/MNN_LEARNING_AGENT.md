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
- returns `None` if no usable matching context exists.

It does **not** silently change the learner's action values or automatically override `decide()`. A caller can inspect the evidence and choose whether to use the recommendation or fall back to the context-free learner. This separation makes memory influence measurable rather than hidden.

## Guarantees and limits

- Rejects overlapping decisions and invalid rewards.
- Records each resolved action outcome as an auditable memory fragment.
- Supports restoring an in-flight action from a JSON-compatible snapshot.
- Does not claim atomic transactions across the learner and SQLite. If memory persistence fails after a learner update, the caller should treat that as a partial failure and recover from its last durable snapshot.
- Retrieval is lexical, not semantic; token overlap can confuse related or ambiguous contexts.
- The action learner is a small contextual-free bandit, not a general planning or consciousness model.
