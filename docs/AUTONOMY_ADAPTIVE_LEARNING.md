# D2 — Adaptive autonomy: strategy learning and retention

## Goal

Demonstrate a stronger claim than D1's preference adjustment: Machina selects
among strategies for a task type, receives an objective reward from a controlled
environment, updates estimates from experience, and uses the learned preference
after its SQLite store is closed and reopened.

## Run locally (Python 3.12+)

```bash
python -m pip install -e .
python -m examples.autonomy_adaptive_learning_demo
python -m unittest discover -s tests -p 'test_autonomy_adaptive_learning.py'
```

## Experiment

The synthetic benchmark has two task types, each with three candidate strategies.
A fixed rubric assigns rewards in [0, 1]. The learner sees only the reward for
the strategy it chose, not the rubric's answer key. It tries unobserved strategies
first, then chooses the strategy with the highest empirical mean reward. The
experience database is reopened before a fresh evaluation, and results are
compared with a fixed `direct` strategy baseline.

## Acceptance criteria

- All six strategy/task-type combinations receive observations during training.
- Learned strategy estimates survive closing and reopening SQLite.
- Post-restart choices are `calculation` for `numeric_reasoning` and `decompose`
  for `information_organization`.
- Mean reward exceeds the fixed-direct baseline on the controlled evaluation.
- Invalid rewards and empty strategy lists are rejected.

## Limits

This is a transparent, deterministic benchmark of narrow reward-based adaptation.
It is not evidence of broad intelligence or generalization beyond these task types:
the benchmark is synthetic, its rubric is fixed, and the evaluation repeats known
task types. It does not demonstrate consciousness or free will. Before claiming
D2 validated, run the demo and tests in Python and inspect the outputs.
