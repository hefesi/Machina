# Operational autonomy validation — D1

This experiment validates one narrow, observable capability in Machina's
operational-autonomy layer: explicit feedback influences later goal selection,
and the adjustment remains available after the SQLite experience store is
closed and reopened.

## Run

From the repository root with Python 3.12 and the package installed:

```bash
python -m pip install -e .
python -m examples.autonomy_operational_demo
python -m unittest tests.test_autonomy_operational_validation
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

## Enquadramento na hipótese fundamental

Esta validação mede autonomia operacional observável, não livre-arbítrio metafísico nem consciência. Os critérios devem diferenciar comportamento reativo, iniciativa endógena, formulação de objetivos, revisão de objetivos e controle persistente. Registrar condições, limites, intervenções externas e explicações alternativas. Relacionar resultados à [Hipótese Fundamental](00-vision/central-hypothesis.md).
