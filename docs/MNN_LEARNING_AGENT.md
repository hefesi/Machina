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
    result = agent.resolve(1.0, context="controlled trial")
    print(result["learning_update"], result["experience_id"])
    print(agent.recall("controlled trial"))
```

## Guarantees and limits

- Rejects overlapping decisions and invalid rewards.
- Records each resolved action outcome as an auditable memory fragment.
- Supports restoring an in-flight action from a JSON-compatible snapshot.
- Does not claim atomic transactions across the learner and SQLite. If memory persistence fails after a learner update, the caller should treat that as a partial failure and recover from its last durable snapshot.
- Recall uses the lexical retrieval implemented by `FragmentMemory`; memories do not automatically alter the policy.
- The action learner is a small contextual-free bandit, not a general planning or consciousness model.
