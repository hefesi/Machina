# D2.3 — Continuous learning and retention

## Goal

Machina accepts new experience in separate sessions, persists feedback as it
arrives, and demonstrates that learning a later task family does not erase
evidence for an earlier family.

## Run

    python -m pip install -e .
    python -m examples.autonomy_d23_continuous_learning_demo
    python -m unittest discover -s tests -p 'test_autonomy_d23_continuous_learning.py'

## Protocol

1. Learn from the prose retrieval task family and write each reward to SQLite.
2. Close the learner to simulate a process/session boundary.
3. Reopen the same database and learn the table retrieval family.
4. Close and reopen again.
5. Evaluate held-out tasks from both families and compare earlier strategy
   statistics before and after the later learning batch.

All candidate strategies are evaluated on each training task. The evaluator
computes exact-match reward; the learner receives only the scalar reward.
The demo expects 18 stored observations across two incremental batches.

## Acceptance criteria

- Earlier experience remains after later learning and restarts.
- The learned strategy remains decompose for prose and checklist for tables.
- Held-out accuracy remains 100% on the four benchmark tasks.
- Automated tests pass.

## Interpretation and limitations

This validates durable, task-family-specific reward history and resistance to
forgetting within this strategy-selection design. It is not a test of neural
network weight consolidation: the learner stores observations in SQLite rather
than updating a neural model. Held-out tasks use new entities and values but
reuse the same narrow templates. No claim is made about broad transfer, AGI,
consciousness, or free will.

## Enquadramento na hipótese fundamental

Aprendizado contínuo precisa ser estudado longitudinalmente: o que muda, o que permanece, como conflitos são resolvidos e como experiências passadas afetam escolhas futuras. Distinguir continuidade de atualização de parâmetros de continuidade de identidade funcional. Não inferir experiência subjetiva a partir de retenção ou adaptação. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).
