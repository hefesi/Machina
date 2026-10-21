# MNN executable core (experimental)

This module introduces a runnable neural substrate in Machina without
replacing the existing durable cognitive loop.

## Concepts

- **Unit**: stable ID, bias, activation function, and current state.
- **Connection**: directed edge with a bounded weight and enabled flag.
- **State transition**: `MNN.step(inputs)` uses a snapshot of the previous
  timestep, computes all targets, and commits states synchronously. Inputs
  clamp matching units for that timestep.
- **Weight plasticity**: `apply_hebbian(learning_rate, reward)` applies
  `Δw = learning_rate × reward × pre_state × post_state`; weights are clamped
  to `[-weight_limit, +weight_limit]`. This is a simple baseline, not a
  biologically complete learning rule.
- **Structural plasticity primitives**:
  - `grow_connection(...)` adds an edge after validating endpoints and
    prevents duplicate directed source/target pairs.
  - `prune_connections(min_abs_weight, max_remove=...)` removes the weakest
    connections below a threshold, deterministically breaking ties by ID.
  - `remove_connection(...)` removes one edge; `remove_unit(..., cascade=True)`
    explicitly removes a unit and its incident edges.
  - These are explicit, testable topology-editing operations. The network does
    **not** yet autonomously choose when or where to grow/prune connections.
- **Persistence boundary**: `snapshot()` returns JSON-compatible topology and
  state; `from_snapshot()` restores it. The MNN does not silently write into
  the existing event journal.

## Minimal example

```python
from machina.mnn import Connection, MNN, Unit

brain = MNN()
brain.add_unit(Unit("sensor", activation="identity"))
brain.add_unit(Unit("integrator", activation="tanh"))
brain.add_connection(Connection("sensor-to-integrator", "sensor", "integrator", 0.7))
print(brain.step({"sensor": 1.0}))
brain.apply_hebbian(learning_rate=0.01, reward=1.0)

# Explicit topology change, for a controlled experiment:
brain.grow_connection("feedback", "integrator", "sensor", weight=0.1)
checkpoint = brain.snapshot()
```

Run tests with `python -m unittest discover -s tests -v` after installing the
project with `python -m pip install -e .`.

## Current limits

## VirtualBrain integration

The optional `MNNCognitionAdapter` wraps the existing cognition component. It
extracts a small, explicit set of normalized numeric features from an
observation, goal, and retrieval count, runs one MNN timestep, and attaches the
activations plus a complete network snapshot to the persisted
`cognition.completed` artifact.

```python
from machina import Connection, MNN, MNNCognitionAdapter, Unit, VirtualBrain

network = MNN()
network.add_unit(Unit("text_input", activation="identity"))
network.add_unit(Unit("signal", activation="tanh"))
network.add_connection(Connection("input-to-signal", "text_input", "signal", 0.8))

adapter = MNNCognitionAdapter(
    network,
    input_features={"text_input": "text_length"},
)
brain = VirtualBrain("machina.sqlite", cognition=adapter)
try:
    result = brain.run_cycle("An observation", "Record it")
finally:
    brain.close()
```

Supported features are `text_length`, `token_count`, `digit_count`,
`punctuation_count`, `goal_length`, `memory_count`, and
`source_reliability`. This is a diagnostic integration: the existing cognition
engine still generates plans, and the numeric MNN signal does not yet control
decisions. The snapshot is stored in the event journal, but automatic
restoration of adapter state across a new process and reward-driven MNN updates
from cycle outcomes are not implemented yet.

## Current limits

This remains an experimental graph substrate, not an autonomous learner or
AGI. It does not implement gradient-based training, autonomous structural
growth policy, asynchronous neural dynamics, or validated task benchmarks.
The adapter is the first observable bridge into the VirtualBrain cycle; the
next step is to define and test how persisted MNN state is restored and how
evaluated outcomes may safely drive plasticity.
