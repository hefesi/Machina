# Strategy self-review

`StrategySelfReviewStore` turns a repeated autobiographical pattern into an
auditable, caller-authored hypothesis proposal. It is a review ledger, not an
autonomous strategy optimizer.

## Example

```python
from machina import ExperienceMemoryStore, StrategySelfReviewStore

experiences = ExperienceMemoryStore("experiences.sqlite3")
report = experiences.autobiographical_report(minimum_repetitions=3)

reviews = StrategySelfReviewStore("strategy-reviews.sqlite3")
proposal = reviews.propose(
    "review-2026-01",
    autobiographical_report=report,
    goal_id="goal:complete-task",
    strategy="baseline",
    alternative_strategy="reduced-scope",
    hypothesis="Reducing task scope may improve the evaluator completion score.",
    rationale="The recorded baseline repeatedly overestimated outcomes.",
    outcome_metric="evaluator completion score",
    confounders=[
        "Task difficulty may vary between attempts.",
        "Evaluator scoring may drift over time.",
    ],
    minimum_repetitions=3,
)

# Approval is an auditable decision, not permission for this store to execute.
decision = reviews.decide(
    "review-2026-01",
    decision_id="decision-2026-01",
    decision="approved",
    rationale="Approved for a separately controlled evaluation.",
    authorization_ref="human-approval:ticket-123",
)
```

## Evidence and safeguards

- A proposal must match exactly one goal/strategy pattern in an
  `ExperienceMemoryStore.autobiographical_report`.
- Evidence references are copied from that pattern and persisted with the
  proposal. The caller supplies the hypothesis, rationale, alternative,
  outcome metric and at least one confounder/limitation.
- The pattern must meet the configured minimum repetition count and carry the
  explicit `repeated_descriptive_pattern_not_causal` interpretation marker.
- Proposal and decision IDs are idempotent; conflicting reuse is rejected.
- Proposals and decisions are stored as separate append-only records. A
  proposal may receive one final decision: `approved` or `rejected`.
- Approval does not start an experiment, execute an action, change a policy,
  update the SelfModel, or grant permissions. A separate experiment runner
  and an independently governed application path would still be required.
- The store does not interpret evaluator notes or generate causal explanations.
  Hypotheses are caller-authored and remain hypotheses until tested.
- This is a functional self-review mechanism, not evidence of subjective
  consciousness or metaphysical free will.

## Intended next integration

An approved proposal can be handed to a separately configured
`CausalExperimentStore` workflow. The experiment protocol, assignment,
measurement, safety constraints and execution authorization must be supplied
and enforced outside this review ledger. Observational associations must not be
reported as causal effects.
