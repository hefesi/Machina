# MNN Concept Guidance

## Purpose

`MNNConceptAdvisor` is a conservative bridge between reviewed concept snapshots and an application's action vocabulary. It does not infer what an action means. The application must explicitly configure a mapping such as `{"stable-context": "continue"}`.

## Decision contract

A recommendation is returned only when:

1. A context tag exactly matches a configured concept key (case-folded and whitespace-normalized).
2. The concept has persisted provenance and its review state is `current`.
3. The current concept status is `supported` and its heuristic confidence clears the configured threshold.
4. No matching concept key is conflicted, and all matched usable concepts map to the same action.

Otherwise, the advisor abstains and provides a reason. If any matched concept is blocked, it abstains rather than quietly ignoring that signal. Evidence IDs and concept IDs are returned for auditing.

## Important limits

- A recurring tag is only a candidate pattern; it is not proof of a causal relationship.
- Confidence is inherited from the concept builder's heuristic, not a calibrated probability.
- The action mapping is supplied by the application and is not learned by the advisor.
- The component does not execute actions, update reward values, or establish consciousness or free will.
- `MNNConceptAdvisor` is an optional policy aid. It does not replace `MNNLearningAgent` or the reward-learning loop.

## Minimal use

```python
from machina import FragmentMemory, MNNConceptAdvisor

advisor = MNNConceptAdvisor(
    memory,
    action_by_concept={"stable-context": "continue"},
    min_confidence=0.5,
)
result = advisor.recommend(["stable-context"])
if result["status"] == "recommended":
    action = result["recommendation"]["action"]
else:
    # Keep the existing policy/fallback; do not invent a recommendation.
    action = None
```

The caller is responsible for applying a safe fallback when the advisor abstains.


## Integration with the learning agent

`MNNLearningAgent` can receive an optional `concept_advisor` and consult it during `decide(use_concepts=True, context_tags=[...])`. A supported recommendation selects its explicitly mapped action for that decision. The ordinary learner still selects a fallback and receives the actual observed reward when `resolve(reward, context=...)` is called. The selected action and reward are archived as an outcome fragment.

When concept guidance abstains, the agent uses the learner's fallback and sets `request_experience=True` so the surrounding environment can collect another outcome. The flag is a request only: no action is executed and no reward is fabricated by the agent.

`benchmarks/mnn_concept_guidance_loop.py` compares this integration with the context-free learner in a small synthetic environment. Since the action mapping and environment rewards are specified in advance, this is an integration smoke benchmark, not evidence that the MNN independently discovered action semantics or will generalize to real tasks.
