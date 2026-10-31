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
