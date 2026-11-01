# Commitment-aware internal autonomy (experimental)

## Purpose

Machina already proposes internal goals from unresolved questions, memory
maintenance, failed cycles, reflection intervals, and sustained motivational
pressure. This extension lets persistent commitments influence the ranking of
those goals without silently changing the commitments or granting new powers.

## Explicit alignment input

`AutonomyController.choose()` and `step()` accept:

- `commitment_alignment`: mapping from candidate `goal_id` to an externally
  assessed alignment value in [0, 1].
- `commitment_weight`: contribution multiplier in [0, 0.15], default 0.10.

The evaluator that produces the mapping must compare a candidate against the
current persistent commitment ledger and preserve evidence/rationale outside
this scoring function. The controller deliberately does not infer alignment
from lexical overlap or self-report. Missing candidates receive alignment 0.

The score adds:

```text
commitment_adjustment = commitment_weight * commitment_alignment
final_score = existing_score + commitment_adjustment
```

The adjustment is bounded to at most 0.15. It is additive and inspectable in
each eligible alternative's score record.

## Safety and invariants

- Commitment alignment cannot bypass the existing risk threshold.
- It cannot bypass explicit authorization for candidates requiring external
  actions.
- It cannot create candidates, execute actions, or mutate the commitment ledger.
- A commitment is not an instruction or permission. External effects remain
  behind the existing authorization boundary.
- Alignment is a supplied assessment, not an objective truth. Store its
  evidence and evaluator identity with the calling experiment.

## Validation

`tests/test_autonomy.py` checks that alignment can change an internal choice,
that values and weight are bounded, and that even maximum alignment cannot
authorize an external action.

## Interpretation

This is a small experiment in operational consistency over time: previously
adopted commitments can exert bounded influence on later internal priorities.
It does not demonstrate a persistent subjective self, consciousness, or
metaphysical free will. A future integration should connect the alignment
assessment to versioned SelfContinuity commitments and auditable evidence,
rather than using text similarity as a substitute.
