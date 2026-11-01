# Curiosity and Knowledge-Gap Goal Proposals

Machina can turn explicitly described knowledge gaps into internal investigation
goals through `SelfModelLearningBridge.propose_curiosity_goals()`.

## Inputs and gating

The caller supplies a mapping from self-model property names to investigation
questions and bounded estimates of information gain, impact, urgency, cost,
and risk. A proposal is eligible when the property is absent/unknown, stale,
or (by default) inferred with confidence no greater than the configured
threshold. Observed beliefs and high-confidence inferred beliefs are not
automatically treated as gaps.

The bridge preserves the current belief's evidence reference and status in
proposal provenance. It does not invent questions from hidden state, claim
that a gap is objectively important, or conduct research itself.

## Value and selection

Expected information value is a transparent heuristic:
`information_gain * impact`. It is used as the candidate's expected benefit,
not as a measured probability. `select_curiosity_goal()` passes the internal
candidates through the existing bounded `AutonomyController`, which ranks
them using its established utility and risk rules.

All generated candidates have `requires_external_action=False`. The caller
cannot override this through mapping data. Selection is not execution and
does not grant access to files, networks, accounts, tools, or other external
resources.

## Interpretation

This is an operational curiosity mechanism: identify a declared knowledge
gap, propose an investigation, and rank it. It is not evidence of subjective
curiosity, intrinsic desire, consciousness, or metaphysical free will.
