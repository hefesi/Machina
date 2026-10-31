# Goal proposals from the operational self-model

## Purpose

Machina can turn explicitly recorded limitations into candidate internal
goals. This connects self-model evidence to autonomy without letting the
self-model invent tasks, select actions, or grant permissions.

## API

SelfModelLearningBridge.propose_goals_from_limitations(goal_mappings)
accepts a caller-authored mapping from an exact known_limitations entry to
a goal description, drive, and optional utility fields. The associated
belief_property defaults to the limitation key.

The default policy accepts only observed beliefs with a non-empty evidence
reference. Unknown and stale beliefs are ignored. Inferred beliefs are
ignored unless allow_inferred=True, their confidence meets
minimum_confidence (default 0.7), and they retain an evidence reference.

The result contains GoalCandidate objects and a parallel provenance list
linking each candidate to the limitation, belief property, status, confidence,
evidence reference, and observation cycle. Candidates are internal-only and
can be passed to AutonomyController.choose(); selection remains a separate
operation.

## Safety and epistemic boundaries

- No mapping means no generated goal; the bridge does not invent plans.
- A limitation string alone is insufficient: it must resolve to a belief with
  admissible status and evidence.
- Inferred beliefs require explicit opt-in and a confidence threshold.
- The bridge does not execute goals, modify the self-model, change commitments,
  or authorize external actions.
- Evidence references are provenance supplied by the caller; their sources
  must be verified by the integrating application.

This is a functional mechanism for self-directed improvement proposals, not
proof of subjective awareness, consciousness, or metaphysical free will.

## Validation

Focused tests cover observed evidence, inferred opt-in, unknown/stale rejection,
confidence thresholds, and provenance preservation.
