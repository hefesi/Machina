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
