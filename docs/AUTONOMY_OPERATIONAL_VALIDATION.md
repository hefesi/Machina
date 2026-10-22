# Operational autonomy validation — D1

This experiment validates one narrow, observable capability in Machina's
operational-autonomy layer: explicit feedback influences later goal selection,
and the adjustment remains available after the SQLite experience store is
closed and reopened.

## Run

From the repository root with Python 3.12:

```bash
python -m pip install -e .
python -m examples.autonomy_operational_demo
python -m unittest discover -s tests -p 'test_autonomy_operational_validation.py'
```

## Expected evidence

- Baseline selection chooses `strategy_a` when both candidates have equal scores.
- Four explicit successful outcomes for `strategy_b` are recorded.
- The experience database is reopened.
- The persisted positive adjustment makes `strategy_b` rank first.
- The demo exits non-zero if these conditions are not met.

## Interpretation and limits

This is a controlled smoke experiment for a small persistent preference update.
It is not evidence of general learning, transfer to real-world tasks, autonomous
task completion, free will, or subjective experience. The feedback is supplied
explicitly by the experiment; the system does not independently verify success.

D1 should only be considered validated after the commands above are executed in
a real Python environment and their outputs are inspected. A code change alone
is not a passing test.
