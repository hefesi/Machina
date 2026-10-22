# MNN reward-plasticity micro-benchmark

## Purpose

This experiment checks whether the current reward-modulated Hebbian update can
learn a deliberately small association. It is designed to be deterministic,
quick to run, dependency-free, and easy to inspect.

It is **not** a test of language understanding, reasoning, broad generalization,
consciousness, or artificial general intelligence.

## Task

The network receives one of two contexts on each trial:

- `context_positive` should produce a response of 1.
- `context_negative` should produce a response of 0.

Both input-to-response weights start at zero. The response uses a sigmoid
activation. A positive-context trial applies reward +1; a negative-context
trial applies reward -1. The benchmark compares the untouched initial network
with a network trained for a fixed number of rounds.

Because MNN state updates are synchronous, each context is presented for two
steps so the response is calculated from the current context before applying
plasticity.

## Run it

From the repository root:

```bash
python -m benchmarks.mnn_reward_learning
python -m unittest discover -s tests -v
```

The script prints JSON containing the benchmark version, training parameters,
baseline and trained accuracy, mean squared error, individual predictions,
final connection weights, and a plain-language limitation statement.

## Interpretation

The expected behavior is that the fixed-weight baseline predicts 0.5 for both
contexts (50% accuracy under the benchmark's `output >= 0.5` threshold), while
reward-modulated plasticity moves the positive-context weight upward and the
negative-context weight downward. The trained model should distinguish these
two repeated contexts under this setup.

This demonstrates only that the specified update rule changes weights in a
way that solves this tiny, engineered association. It does not establish
out-of-distribution generalization, transfer, robustness, or superiority to
transformers or other neural architectures. A meaningful next benchmark must
include held-out patterns/tasks, multiple random seeds where applicable,
ablations, stronger baselines, and uncertainty reporting.
