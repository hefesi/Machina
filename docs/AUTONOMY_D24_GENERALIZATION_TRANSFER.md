# D2.4 — Generalization and transfer

## Goal

Measure whether Machina can reuse a strategy learned on known task families
when the task family, question phrasing, and record syntax are new.

## Experiment

- Train only on D2.2 prose and pipe-table examples (18 reward observations).
- Persist to SQLite and restart the learner.
- Evaluate four tasks in two withheld formats: bullet records and bracketed
  `record[Entity]{field="value"}` records.
- Use new question phrasing ("Find ... belonging to ..." / "Locate ... for ...").
- Compare against a fixed `direct` strategy and a cold learner with no history.

For a task family with no task-specific evidence, the learner now falls back to
global strategy reward estimates. Existing task-specific evidence remains the
preferred choice whenever available.

## Run

    python -m pip install -e .
    python -m examples.autonomy_d24_generalization_transfer_demo
    python -m unittest discover -s tests -p 'test_autonomy_d24_generalization_transfer.py'

## Acceptance criteria

- The learner selects the strategy with the strongest transferred evidence.
- Transfer accuracy exceeds both baselines.
- The experience store still contains the 18 training observations after restart.
- The focused test suite passes.

## Interpretation and limitations

This is a small, deterministic structural-transfer test. The strategy parser has
explicit support for the withheld syntaxes, so the experiment tests whether
learned strategy selection transfers to unseen task families—not whether the
system invents a parser for arbitrary formats. Four test cases are not enough to
claim broad generalization, robust reasoning, AGI, consciousness, or free will.
A later stage should use randomized examples, more formats, adversarial distractors,
and a held-out test set not authored alongside the implementation.
