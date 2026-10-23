# MNN F3 — Retention, interference, and forgetting

## Objective

Measure three distinct effects in a small deterministic MNN experiment:

1. **Retention under unrelated learning:** train an association from `cue_a`
   to a positive response, then learn a separate association from `cue_b`.
   The first association should remain unchanged.
2. **Cue omission:** evaluate with neither cue active. The output should be
   absent even though the learned `memory_a` weight is still present. This
   separates a missing activation from deletion of the parameter in this toy
   system; it is not a complete model of biological or semantic retrieval.
3. **Interference:** repeatedly pair `cue_a` with the opposite response.
   The same Hebbian edge should change sign and reverse the output.
4. **Persistence:** save and reload the resulting MNN checkpoint and confirm
   that the changed weight and behavior survive restoration.

## Run

```bash
python -m benchmarks.mnn_retention_interference
python -m unittest tests.test_mnn_retention_interference -v
python -m unittest discover -s tests -v
```

The benchmark uses fixed inputs, a fixed learning rate, and no external data.
Its assertions make the intended outcome reproducible.

## Interpretation and limits

This experiment demonstrates that an unrelated connection can be learned
without changing an existing connection, and that contradictory training can
modify the same connection. It also demonstrates that checkpoint persistence
preserves the current parameters, including changed parameters.

It does **not** establish human-like forgetting, autobiographical continuity,
semantic retrieval, robust continual learning, or consciousness. A missing
cue yielding no response is only a controlled probe of cue availability. In
this version, the benchmark does not use the fragment-memory store's dynamic
priority/decay mechanism; that should be evaluated separately so parameter
interference is not confused with fragment eviction or retrieval ranking.
