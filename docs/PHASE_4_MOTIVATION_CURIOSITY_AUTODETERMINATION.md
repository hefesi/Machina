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
