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
