# Phase 4 — Motivation, curiosity and operational self-determination

## Architecture

This increment builds on the existing `MotivationSystem`, `AutonomyController`,
`PersistentGoalStore` and `GoalReviewer`. The new `CuriositySelector`
ranks explicit knowledge-gap proposals using uncertainty, expected information
gain, relevance, novelty, estimated cost and risk.

Exploration is not tied to immediate external reward. A stability-pressure
signal reduces the exploration weight, while repeated questions receive a
penalty. Risky candidates and candidates requiring external action are rejected
by default.

### Implemented selector contract

`CuriosityCandidate` represents one caller-proposed knowledge gap with
explicit uncertainty, expected information gain, relevance, novelty, cost,
risk, and evidence references. `CuriositySelector.rank()` returns a
`CuriosityDecision` containing the selected candidate, a deterministic
ranked alternative list with score components, and rejection reasons.

`stability_pressure` is bounded to [0, 1] and scales exploration-related
terms by `1 - 0.75 * stability_pressure`. Prior questions are normalized by
case and whitespace before the repetition penalty is applied. Risk above the
configured maximum and any candidate requiring external action are rejected.
The selector is deliberately a pure ranking component; it does not create
investigations in `CuriosityInvestigationStore` or execute a selected goal.

Example:

```python
from machina import CuriosityCandidate, CuriositySelector

selector = CuriositySelector(max_risk=0.4)
decision = selector.rank(
    [CuriosityCandidate(
        candidate_id="gap-1",
        gap_property="memory.coherence",
        question="Which observation explains this contradiction?",
        hypothesis="The records may refer to different contexts.",
        uncertainty=0.8,
        expected_information_gain=0.9,
        relevance=0.9,
        novelty=0.7,
        estimated_cost=0.2,
        risk=0.05,
        evidence_refs=("memory:12", "observation:31"),
    )],
    stability_pressure=0.2,
    prior_questions=(),
)
```

## Evidence boundary

The caller supplies each question, hypothesis and numerical estimate. The
selector ranks proposals; it does not conduct research, verify evidence or
automatically change beliefs. The scores are inspectable engineering signals,
not proof of subjective curiosity, consciousness or metaphysical free will.

## Completion experiments

1. Raise internal drive pressure and inspect how existing autonomy changes goal ranking.
2. Compare knowledge gaps with different uncertainty and information-gain estimates.
3. Increase stability pressure and verify exploration weight falls.
4. Repeat a recent question and verify its repetition penalty.
5. Verify high-risk and unauthorized external-action candidates are rejected.
6. Feed new evidence to the existing goal-review process and require explicit review before applying a revision.

The phase is complete only when end-to-end traces retain candidate scores,
alternatives, evidence provenance and review outcomes.
