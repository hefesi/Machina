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
neurotransmitter molecules. The coordinator does not yet integrate the VirtualBrain event journal. Episodic memory can be attached as a separate persistence domain, as described below.


## Episodic memory coupling

`MNNOrganism` can now receive an existing `FragmentMemory` instance. When
attached, every successful integrated transition writes one immutable episode
fragment containing the agent ID, logical timestep, neural activations,
virtual chemical concentrations, reward-prediction error, modulation outputs,
and any weight changes. Episode IDs are deterministic for an agent/timestep,
so a repeated write is rejected rather than silently overwriting a prior
experience.

The archive remains a separate SQLite persistence domain and is not embedded
inside the organism snapshot. This is deliberate: the organism checkpoint
captures dynamic internal state, while FragmentMemory owns durable episodic
records. Reopen the same memory database after process restart and attach it to
the restored organism to continue recording and recalling episodes.

`recall_experiences(query, limit, context)` delegates to the existing
explainable lexical/associative retrieval baseline. It does not imply semantic
understanding, autobiographical self-awareness, or that retrieved episodes
automatically influence cognition. The next integration experiment must test
whether retrieved experience changes a downstream decision and improves
held-out performance against a no-retrieval baseline.



## Explicit memory-to-neural guidance (experimental)

Memory retrieval can now be turned into an explicit neural input without
making retrieval an invisible side effect of every cycle:

```python
guidance = organism.prepare_memory_guidance(
    "prediction error",
    target_unit="memory_context",
)
state = organism.step(memory_guidance=guidance)
```

The returned `MemoryGuidance` contains the original query, target unit,
bounded signal, evidence fragment IDs, and per-fragment scores. The current
signal is a confidence-weighted lexical token-overlap baseline. It is not
semantic similarity, truth estimation, or proof that a recalled episode is
relevant to the present situation. If no evidence matches, the signal is zero
and the evidence list is empty.

The target must be an existing MNN unit and cannot conflict with another
input route in the same step. Preparing guidance does not advance the neural
clock or rewrite memory; only passing it explicitly to `step` routes it into
the designated unit. This keeps the causal path inspectable and makes
retrieval-versus-no-retrieval experiments possible.

Tests cover evidence routing, zero-signal abstention for unrelated queries,
route conflicts, and the fact that preparation itself does not change the
organism snapshot. This is an integration primitive, not yet evidence that
memory improves decisions or generalization. The next experiment is a
controlled task where memory-guided and no-memory conditions are compared on
held-out examples.


## Outcome-based contextual memory feedback (experimental)

The organism now exposes `evaluate_memory_guidance(...)` to record whether
specific retrieved fragments were useful in an explicitly named task context.
The caller supplies boolean outcomes; the organism does not infer usefulness
from neural activation, prediction error, or a successful-looking response.
Feedback is restricted to fragment IDs present in the corresponding
`MemoryGuidance` evidence set.

The operation delegates to FragmentMemory's context-specific feedback ledger.
Positive and negative labels adjust a bounded relevance score for that context
without changing the fragment's global importance or other task contexts. When
the same context is supplied to a later `prepare_memory_guidance(...,
context="route-planning")` call, its learned relevance scales the evidence
signal (neutral score 0.5 leaves the lexical signal unchanged). A stable
`operation_id` makes retries idempotent, and the feedback history is auditable. Example:

```python
scores, applied = organism.evaluate_memory_guidance(
    guidance,
    {guidance.evidence_ids[0]: True},
    context="route-planning",
    operation_id="route-planning-eval-0001",
)
```

This closes a minimal feedback loop: retrieve evidence, expose it to an
explicit neural input, evaluate its usefulness externally, and update
context-specific retrieval relevance. It does not yet establish that this
feedback improves decisions. That claim requires controlled, held-out
experiments with fixed datasets, repeated seeds, and retrieval/no-retrieval
baselines. The feedback label must come from a defined evaluator or outcome,
not from the model's own unsupported assertion that a memory was useful.


## Memory-informed alternative assessment (experimental)

The organism can now compare a caller-supplied set of candidate actions with
`assess_decisions(...)`. Each `DecisionOption` contains an action label, an
externally estimated base utility, and a query used to retrieve relevant
episodes. The assessment adds a bounded memory contribution to each base
utility and returns the selected action, per-action scores, evidence IDs, and
the selected option's `MemoryGuidance`.

This is deliberately a deliberation primitive, not an autonomous action
executor. It does not invent alternatives, estimate base utility, or execute
the winner. The caller can inspect the assessment and explicitly pass
`selected_guidance` to a subsequent organism step. Ties are resolved by
action name for deterministic behavior.

Example:

```python
from machina import DecisionOption

assessment = organism.assess_decisions(
    [
        DecisionOption("reuse-experience", 0.40, "prediction error"),
        DecisionOption("unfamiliar-route", 0.55, "volcano astronomy"),
    ],
    target_unit="memory_context",
    context="route-planning",
    memory_weight=0.25,
)
# Inspect assessment, then explicitly apply its selected memory guidance.
organism.step(memory_guidance=assessment.selected_guidance)
```

A higher score in this baseline only means the configured arithmetic favored
that option. It does not show that the action is objectively better. Base
utilities and usefulness labels need external ground truth. The next
validation must measure held-out task outcomes against a no-memory baseline,
including negative feedback, misleading memories, and cases where recalling
an experience should not change the decision.


## Persistent homeostatic motivation (experimental)

The module `machina.mnn_motivation` introduces explicit, persistent drive
variables. Each `MotivationalDrive` has a current deficit level, a setpoint,
a priority, a recovery rate, and a fulfillment sensitivity. On each logical
step, an unmet drive recovers toward its setpoint; an externally recorded
fulfillment outcome reduces its deficit. The `MotivationSystem` ranks drives
by priority-weighted urgency and supports versioned snapshots.

```python
from machina import MotivationalDrive, MotivationSystem

motivation = MotivationSystem([
    MotivationalDrive("curiosity", level=0.8, setpoint=0.8, priority=0.7),
    MotivationalDrive("stability", level=0.6, setpoint=0.6, priority=1.0),
])
print(motivation.ranked_drives())
motivation.step({"stability": 1.0})
```

Fulfillment is explicit input from an evaluator or environment; the system
does not declare its own actions successful. A drive is a computational
deficit variable, not a biological need or felt desire. Priority-weighted
urgency is a control signal, not evidence of intrinsic subjective motivation.

This first primitive is intentionally separate from `MNNOrganism` so that
its dynamics can be tested before coupling it to neural activity, chemical
signaling, persistent goals, and action selection. The next integration
experiment should test whether changing drive deficits causes measurable,
adaptive differences in goal selection without destabilizing the system.


### Motivation-to-goal selection coupling

`MotivationSystem.autonomy_adjustments()` exposes the current urgency of each
drive as bounded feedback keyed by drive name. Pass this mapping to
`AutonomyController.choose(..., drive_adjustments=...)` or
`AutonomyController.step(..., drive_adjustments=...)`. With the default gain,
urgency 0.5 is neutral and the extremes map to -0.15/+0.15, matching the
controller's existing feedback clamp.

```python
from machina import (
    AutonomyContext, AutonomyController,
    MotivationalDrive, MotivationSystem,
)

motivation = MotivationSystem([
    MotivationalDrive("curiosity", level=0.9, priority=1.0),
    MotivationalDrive("stability", level=0.3, priority=1.0),
])
controller = AutonomyController()
decision = controller.step(
    AutonomyContext(unresolved_questions=2),
    drive_adjustments=motivation.autonomy_adjustments(),
)
```

This coupling biases the ranking of goals that already exist in the autonomy
controller; it does not create a new goal for every drive. Goal generation
remains bounded by the controller's explicit candidate rules and safety
filters. The motivational state is still a separate persistence domain and
must be snapshotted/restored by its owner. Tests verify that changing drive
urgency changes goal ranking while retaining the controller's risk and
external-action restrictions.


### Internal motivation as a chemical-signaling input

`MotivationSystem.chemical_pressure` computes the mean urgency across its
configured drives (zero when no drives exist). A caller can pass that scalar
into `ChemicalEvent.motivational_pressure` on the next chemical transition:

```python
from machina import ChemicalEvent, ChemicalSignaling, MotivationSystem

pressure = motivation.chemical_pressure
chemical_update = ChemicalSignaling().step(
    ChemicalEvent(
        novelty=0.2,
        uncertainty=0.3,
        risk=0.1,
        motivational_pressure=pressure,
    )
)
```

Motivational pressure contributes to virtual acetylcholine and noradrenaline
targets and to the exploration-drive calculation. It is an additional internal
input, not a replacement for externally observed reward, novelty, uncertainty,
or risk. The mapping is deliberately explicit and inspectable; it is not a
claim that these neurotransmitters have been biologically reproduced. The
caller controls update order: evaluate current drive urgency, advance chemical
signaling with that pressure, then apply explicitly observed fulfillment to
the motivation system. This prevents the chemical layer from silently
declaring a drive satisfied.
