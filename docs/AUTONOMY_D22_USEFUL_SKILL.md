# D2.2 — Useful skill learning with held-out evaluation

## Objective

Move beyond a synthetic reward table: Machina must perform a concrete information
retrieval task, receive reward from exact-match evaluation, retain task-specific
strategy estimates, and use those estimates on new records after the SQLite store
has been closed and reopened.

## Run (Python 3.12+)

```bash
python -m pip install -e .
python -m examples.autonomy_d22_useful_skill_demo
python -m unittest discover -s tests -p 'test_autonomy_d22_useful_skill.py'
```

## Task and strategies

The skill answers questions of the form `What is the <field> for <entity>?`.
Contexts use either short prose facts or structured pipe-delimited rows. Candidate
strategies are:
- `direct`: returns the first value it encounters, without matching the query;
- `decompose`: matches both entity and field in prose;
- `checklist`: scans structured rows for an exact entity + field match.

The evaluator compares the predicted answer to a known answer and returns 1.0 for
an exact match or 0.0 otherwise. The learner receives only this scalar reward.

## Experiment controls

- Training: every strategy is evaluated on each of six labeled training tasks
  (18 reward observations total).
- Persistence: close and reopen SQLite before held-out evaluation.
- Held-out set: four new records with new entities and values, using the same two
  input formats.
- Control A: always use `direct`, with no learning.
- Control B: use a fresh learner with no stored experience.

## Acceptance criteria

- The persisted learner chooses `decompose` for prose and `checklist` for tables.
- It answers all four held-out tasks correctly.
- Its held-out exact-match accuracy exceeds both controls.
- Automated tests pass.

## Limitations

This is a small, deterministic benchmark using deliberately narrow templates.
The held-out entities and values are new, but the formats and task types are not.
It supports a modest claim of task-specific strategy selection and retention, not
general language understanding, broad transfer, consciousness, or free will.
A larger and more varied benchmark is required before stronger claims.
