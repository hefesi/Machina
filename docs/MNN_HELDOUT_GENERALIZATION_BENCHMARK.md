# MNN Held-Out Generalization Benchmark v0.1

## Question

Can reward-modulated eligibility learning use examples to learn a simple rule
that applies to a feature combination withheld from training, and preserve that
behavior through a checkpoint round trip?

## Task

The network receives two binary features, A and B, plus their negations. The
target is positive when A or B is present. Training uses only these contexts:

- A=true, B=false (positive)
- A=false, B=true (positive)
- A=false, B=false (negative)

The combination A=true, B=true is held out until evaluation. The benchmark
compares reward-modulated eligibility learning with fixed zero weights and
immediate reward-modulated Hebbian updates. Both learning rules share the same
network substrate and task; this is a narrow baseline comparison, not proof that
one family of algorithms is universally superior.

## Run

From the repository root:

```bash
python -m benchmarks.mnn_generalization
python -m unittest discover -s tests -p 'test_mnn_generalization.py' -v
```

## Acceptance criteria

1. The trained network predicts the held-out A+B context correctly.
2. Its held-out mean squared error is lower than the fixed-weight baseline.
3. Learned connection weights are identical after restoring a checkpoint into
   fresh network and learner objects.
4. Predictions before and after restoration are identical.
5. Automated tests pass.

The JSON output reports training metrics, held-out metrics for reward learning,
fixed weights and immediate Hebbian learning, plus checkpoint-retention results.

## Limitations

This is a deterministic, tiny feature-combination task with one held-out
context. It is vulnerable to task-specific design choices and is not evidence
of robust generalization, causal reasoning, language understanding, autonomy,
consciousness, or AGI. The next research step should evaluate multiple held-out
combinations, noisy/distractor inputs, different seeds and learning rates, and
more rigorous controls.
