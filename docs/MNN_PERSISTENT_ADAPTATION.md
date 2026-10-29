# MNN Persistent Adaptation Benchmark

Run from the repository root:

```bash
python -m benchmarks.mnn_persistent_adaptation
```

## Experiment

1. The action learner observes a deterministic environment in which `left` earns 1 and `right` earns 0.
2. Its snapshot is written as JSON, then reconstructed as a fresh learner instance.
3. A SQLite fragment-memory archive records the original mapping and the explicit environment shift.
4. The second phase reverses the mapping: `right` earns 1 and `left` earns 0.
5. The benchmark reopens SQLite and verifies that the change record remains retrievable.

The experiment reports reward rate over each phase and the last ten decisions, action counts, predicted values, restart integrity, and memory recall. It is deterministic and designed to catch regressions in learning, adaptation, and persistence.

## Pass criteria

- The final-ten reward rate in both phases is at least 0.8.
- The preferred action's learned value is greater than the alternative at the end of each phase.
- The learner snapshot is unchanged by JSON serialization and restoration.
- Both memory fragments remain in SQLite and the environment-shift fragment is retrievable.

## Scope and limitations

This is a small two-action bandit task with deterministic rewards. It does not demonstrate generalization to unseen contexts, causal understanding, biological dopamine, consciousness, or general intelligence. The action learner and fragment memory remain separate subsystems coordinated by the experiment; the memory record documents the environment change rather than autonomously changing the learner's policy.

## Enquadramento na hipótese fundamental

Adaptação persistente deve ser verificada por experimentos longitudinais que examinem retenção, reversibilidade, estabilidade e efeitos em contextos posteriores. A persistência de parâmetros é um requisito técnico possível, mas não equivale automaticamente à continuidade de identidade. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).
