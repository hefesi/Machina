# MNN executable core (experimental)

Machina now contains a runnable, stateful graph substrate and an optional
adapter into the VirtualBrain cognitive cycle. This is an experimental
research implementation, not evidence of general intelligence.

## Core model

- **Unit**: stable ID, bias, activation function, and current state.
- **Connection**: directed edge with a bounded weight and enabled flag.
- **State transition**: `MNN.step(inputs)` uses a snapshot of the previous
  timestep, computes all targets, and commits states synchronously. Inputs
  clamp matching units for that timestep.
- **Weight plasticity**: `apply_hebbian(learning_rate, reward)` applies
  `Δw = learning_rate × reward × pre_state × post_state`; weights are clamped
  to `[-weight_limit, +weight_limit]`. This is a simple baseline, not a
  biologically complete or generally effective learning rule.
- **Structural plasticity primitives**:
  - `grow_connection(...)` adds an edge after validating endpoints and
    prevents duplicate directed source/target pairs.
  - `prune_connections(min_abs_weight, max_remove=...)` removes the weakest
    connections below a threshold, deterministically breaking ties by ID.
  - `remove_connection(...)` removes one edge; `remove_unit(..., cascade=True)`
    explicitly removes a unit and its incident edges.
  - These are explicit, testable topology-editing operations. The network does
    **not** yet autonomously choose when or where to grow/prune connections.
- **Snapshots**: `snapshot()` returns JSON-compatible topology and state;
  `from_snapshot()` restores it.

## VirtualBrain integration and durable learning

The optional `MNNCognitionAdapter` wraps the existing cognition component. It
extracts a small set of normalized numeric features from an observation, goal,
and retrieval count, runs one MNN timestep, and attaches activations and a
network snapshot to the persisted `cognition.completed` artifact.

The existing cognition engine remains responsible for candidate plans. MNN
activations are diagnostic and do not independently select actions.

After an evaluation and validation stage, the adapter can propose a reward
modulated Hebbian update: success receives reward `+1`, failure receives
reward `-1`. The proposed snapshot and weight deltas are written as an
`mnn.plasticity_applied` journal event before the live adapter restores that
snapshot. This journal-first ordering supports recovery and prevents the same
reward from being applied twice when a cycle resumes. The neural weight update
is distinct from semantic-memory consolidation; it does not automatically make
a failed proposal into a trusted memory.

Before the next cognitive cycle, VirtualBrain restores the latest MNN snapshot
from persisted cognition/plasticity events. Regression tests cover process
restart and exactly-once recovery behavior.

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

## Reproducible benchmark

Run the deterministic toy association experiment from the repository root:

```bash
python -m benchmarks.mnn_reward_learning
```

It compares initial fixed weights with reward-trained weights on two simple
contexts and reports accuracy, mean squared error, and final weights as JSON.
The test suite checks determinism and expected behavior. This is a smoke test
for the plasticity implementation, **not** a meaningful benchmark of language,
reasoning, broad generalization, or AGI. The baseline is deliberately simple
and is not a competitive model. See [MNN reward-learning benchmark](MNN_BENCHMARK.md).

Run tests with `python -m pip install -e .` followed by
`python -m unittest discover -s tests -v`.

## Current limitations

This remains an experimental graph substrate. It does not yet implement
gradient-based training, a validated general-purpose learning objective,
autonomous structural-growth policy, asynchronous neural dynamics, semantic
understanding grounded in the MNN signal, or evidence of AGI. The next research
step is to evaluate learning and generalization on diverse, held-out tasks
against stronger and clearly specified baselines.

## Enquadramento na hipótese fundamental

O núcleo executável da MNN deve ser entendido como um substrato experimental, não como uma mente completa nem como evidência de consciência. A documentação técnica precisa separar capacidades realmente implementadas, hipóteses ainda não testadas e capacidades que existem apenas como especificação. Relacionar cada experimento à contribuição para a dinâmica integrada e persistente de Machina. Ver [Hipótese Fundamental](00-vision/central-hypothesis.md).


## Integrated persistent organism cycle (experimental)

The new `MNNOrganism` coordinator joins three previously separate state
domains in one logical transition:

1. virtual chemical signaling updates its persistent concentrations and
   reward-prediction error;
2. configured chemical outputs can be routed into named MNN units before the
   synchronous neural transition;
3. optional reward-modulated Hebbian adaptation uses prediction error and the
   bounded virtual plasticity gain; and
4. the functional continuity ledger records the transition under one stable
   agent identifier.

The coordinator rejects mismatched neural/chemical clocks and identity IDs.
Its versioned snapshot includes topology, neural activations, chemical
concentrations, continuity history, routing configuration, and learning rate.
A restored instance can continue with the same deterministic next transition.

Example:

```python
from machina import ChemicalEvent, Connection, MNN, MNNOrganism, Unit

network = MNN()
network.add_unit(Unit("sensor", activation="identity"))
network.add_unit(Unit("dopamine", activation="identity"))
network.add_unit(Unit("integrator", activation="tanh"))
network.add_connection(Connection("sensor-integrator", "sensor", "integrator", 0.4))
network.add_connection(Connection("dopamine-integrator", "dopamine", "integrator", 0.2))

organism = MNNOrganism(
    "machina-01",
    network,
    chemical_inputs={"dopamine": "dopamine"},
    learning_rate=0.01,
)
state = organism.step(
    {"sensor": 0.7},
    ChemicalEvent(reward=0.8, novelty=0.6),
)
checkpoint = organism.snapshot()
```

This is a functional integration milestone, not an autonomous organism, a
complete cognitive architecture, or evidence of subjective experience. The
chemical variables are computational control signals, not simulated
neurotransmitter molecules. The coordinator also does not yet integrate the
VirtualBrain event journal or semantic/episodic memory repository; those
remain separate persistence domains and are explicit next integration work.
