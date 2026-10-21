# MNN executable core (experimental)

This module introduces the first runnable neural substrate in Machina without
replacing the existing durable cognitive loop.

## Concepts

- **Unit**: stable ID, bias, activation function, and current state.
- **Connection**: directed edge with a bounded weight and enabled flag.
- **State transition**: `MNN.step(inputs)` uses a snapshot of the previous
  timestep, computes all targets, and commits states synchronously. Inputs
  clamp matching units for that timestep.
- **Plasticity**: `apply_hebbian(learning_rate, reward)` applies
  `Δw = learning_rate × reward × pre_state × post_state`; weights are clamped
  to `[-weight_limit, +weight_limit]`. This is a deliberately simple
  baseline, not a biologically complete learning rule.
- **Persistence boundary**: `snapshot()` returns JSON-compatible topology and
  state; `from_snapshot()` restores it. This first version does not silently
  write into the existing event journal.

## Minimal example

```python
from machina.mnn import Connection, MNN, Unit

brain = MNN()
brain.add_unit(Unit("sensor", activation="identity"))
brain.add_unit(Unit("integrator", activation="tanh"))
brain.add_connection(Connection("sensor-to-integrator", "sensor", "integrator", 0.7))
print(brain.step({"sensor": 1.0}))
brain.apply_hebbian(learning_rate=0.01, reward=1.0)
checkpoint = brain.snapshot()
```

Run tests with `python -m unittest discover -s tests -v`.

## Current limits

This is a deterministic graph substrate, not yet an autonomous learner or AGI.
There is no gradient-based training, structural plasticity, asynchronous
neural dynamics, task benchmark, or integration into the VirtualBrain cycle.
Those should be added as separate, tested steps after this primitive is
reviewed.
