# Self-prediction and evidence-based calibration

## Purpose

A self-model that only records current beliefs describes state. A predictive
self-model can additionally state what it expects to happen and later compare
that expectation with an outcome. This creates an observable prediction-error
signal without assuming introspective awareness or subjective experience.

## API

`SelfModel.predict()` records a prediction with:

- a unique prediction reference;
- the operational property being predicted;
- a JSON-compatible predicted value;
- the cycle in which the prediction was made;
- an explicit horizon label;
- a confidence in [0, 1].

`SelfModel.evaluate_prediction()` later requires the prediction reference,
the actual value, an evaluation cycle, and an evidence reference. It compares
the predicted and actual values using exact equality and records a generic
error of 0.0 (match) or 1.0 (mismatch).

Each prediction can be evaluated only once. Unknown references and duplicate
prediction IDs are rejected. Both predictions and evaluations are retained in
the snapshot and restored with validation. Older schema-v1 snapshots that do
not contain the new prediction collections remain readable.

## Why exact-match error?

The self-model accepts arbitrary JSON-compatible values, not only numbers.
There is no universal distance function for booleans, strings, structured
objects, and numeric measurements. Exact-match error is therefore deliberately
simple and interpretable. Numeric or domain-specific metrics should be
introduced by named evaluators with explicit units and normalization, not
silently inferred by the generic self-model.

## Example

```python
model.predict(
    "runtime_available", True,
    prediction_ref="runtime-prediction-17",
    cycle_id="cycle-17",
    confidence=0.8,
    horizon="next_cycle",
)

result = model.evaluate_prediction(
    "runtime-prediction-17",
    False,
    cycle_id="cycle-18",
    evidence_ref="runtime-check-18",
)
# result["matched"] is False; result["error"] is 1.0
```

The evidence reference is provenance supplied by the caller. The model does
not independently verify that external evidence source; integrations must
ensure that the reference resolves to a trustworthy observation or artifact.

## Research boundary

This mechanism makes expectations falsifiable and preserves their outcomes.
It does not establish that the system has introspective access, a subjective
sense of self, consciousness, or metaphysical free will. Confidence is a
recorded estimate, not a guarantee of calibration. Calibration quality must
be measured over many predictions, including selection effects and missing
evaluations.


## Longitudinal calibration report

`SelfModel.calibration_report()` aggregates predictions by property and
horizon, with optional filters. It reports emitted, evaluated, and pending
counts; evaluation coverage; exact-match accuracy; mean declared confidence;
and the signed calibration gap (mean confidence minus observed accuracy).
Confidence is explicitly interpreted as the estimated probability that the
entire predicted value will match exactly.

Pending predictions are excluded from accuracy and confidence averages, not
silently counted as failures. Coverage is reported alongside the metrics
because the set of evaluated predictions may be selection-biased. With no
evaluated predictions, accuracy, mean confidence, and calibration gap are
`None` rather than misleading zeros. Group summaries are deterministic
and derived from persisted history. The report is read-only: it does not
self-adjust confidence or affect autonomy, action execution, or authorization.
This is an empirical diagnostic, not a complete statistical calibration
study; Brier scores are deferred until a separately specified binary-outcome
prediction contract exists.


Confidence values are estimates supplied at prediction time, not probabilities
derived from a trained probabilistic model. The report therefore measures
agreement between those declared estimates and empirical exact-match frequency;
it does not certify statistical calibration from small samples.
