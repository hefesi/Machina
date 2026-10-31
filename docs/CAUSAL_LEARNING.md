# Evidence-bounded causal learning

## Scope

`CausalExperimentStore` records explicitly registered experiments and
evaluator-supplied outcomes. It separates randomized comparisons, matched
comparisons, and observational associations. It does not infer causality from
ordinary chronological correlations.

## Experiment designs

- `randomized`: requires a protocol reference and compares treatment/control
  group means after a minimum sample in each arm.
- `matched`: requires a context key and compares only complete treatment/
  control pairs.
- `observational`: reports group means and labels the result as an
  observational association. It never emits a causal effect estimate.

Outcomes are normalized to [0, 1]. Reports include a mean difference,
standard error, and a normal-approximation 95% interval for eligible randomized
or matched comparisons. The default minimum is five units per arm/pair.

## Counterfactual boundary

The reported contrast is a group-average estimate. The unobserved outcome for
the same individual under the alternative treatment cannot be directly
observed. The report therefore does not claim to know an individual
counterfactual. Matched comparisons estimate average paired contrasts only
when both arms exist for the same context key.

## Trust and assumptions

The caller supplies assignment design, protocol reference, outcome, context,
and evidence references. The store cannot verify random assignment, adherence,
blinding, measurement quality, or the absence of interference/confounding.
Confidence intervals are approximations, not proof of causality. Evidence
references must be audited by the integrating application.

This module is a measurement primitive. It does not automatically update
self-beliefs, alter autonomy scores, select goals, or authorize actions.


## Causal experiment → inferred self-belief bridge

`SelfModelLearningBridge.update_belief_from_causal_experiment()` is an
explicit, opt-in projection of one experiment report into one operational
self-belief. It accepts only reports classified as randomized or matched
comparisons, requires the configured minimum sample, requires the approximate
95% interval to exclude zero, and applies a minimum absolute effect threshold.
Observational associations and insufficient/uncertain results are rejected
without mutating the self-model.

Accepted beliefs are always marked `inferred`, never `observed`. The belief
stores the group-level effect, interval, standard error, sample counts,
declared design, protocol reference, and trial evidence references. The
confidence field is an evidence-support heuristic based on sample size; it is
not a probability that the claim is true and is not a statistical confidence
level. Reapplying the same experiment evidence to the same property is
idempotent.

The bridge does not validate the experiment's random assignment or protocol
adherence, does not infer individual counterfactuals, and does not alter
autonomy, goals, MNN weights, or action permissions. A downstream consumer
must independently decide whether and how inferred beliefs may influence
behavior.

## Append-only belief revision history

The self-model exposes `belief_revision_history` and `revise_belief()`. An
explicit revision requires an existing belief, a new evidence reference, a
reason, and a source. Each record preserves detached previous/new values,
status, confidence, cycle, and whether the caller's domain-specific comparison
found a contradiction. Snapshot restore validates contiguous sequence numbers
and consistency between the latest revision and the current belief. Older
snapshots without this optional history still load.

When distinct eligible causal evidence updates an existing causal belief, the
bridge uses this revision API rather than silently overwriting it. Opposite
signs in estimated group effects are flagged as contradictions, not treated
as proof that either experiment is correct. This history is descriptive and
append-only; it does not automatically change autonomy or execution policy.