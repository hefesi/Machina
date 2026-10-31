# MNNOrganism ↔ VirtualBrain Bridge (experimental)

## Purpose

MNNOrganismCognitionAdapter connects the integrated organism to the existing durable VirtualBrain cognition stage. It does not replace MNNCognitionAdapter, duplicate memory, or merge the two orchestration layers.

- MNNOrganism remains responsible for neural state, virtual chemical signaling, motivation, functional continuity, and any attached FragmentMemory.
- VirtualBrain remains responsible for cognitive cycles, decisions, actions, evaluations, and the append-only event journal.
- MNNOrganismCognitionAdapter maps explicitly configured observation features to organism input units, advances one organism tick, and attaches a complete organism snapshot to the cognitive artifact.

## Configuration

```python
from machina import (
    Connection, MNN, MNNOrganism,
    MNNOrganismCognitionAdapter, Unit, VirtualBrain,
)

network = MNN()
network.add_unit(Unit("sensor", activation="identity"))
network.add_unit(Unit("integrator", activation="tanh"))
network.add_connection(Connection("sensor-integrator", "sensor", "integrator", 0.4))

organism = MNNOrganism("machina-01", network=network, learning_rate=0.0)
cognition = MNNOrganismCognitionAdapter(
    organism,
    input_features={"sensor": "text_length"},
)

with VirtualBrain("data/brain.sqlite", cognition=cognition) as brain:
    result = brain.run_cycle(
        "A new observation enters the organism.",
        "Interpret and evaluate the observation.",
    )
```

Supported deterministic features: text_length, token_count, digit_count, punctuation_count, goal_length, memory_count, and source_reliability. Input unit IDs and feature names are validated during construction.

## Persistence and recovery

The adapter stores its snapshot under the existing understanding.mnn_signal.snapshot path. VirtualBrain restores the latest snapshot from its append-only journal before processing a new cognitive cycle. This preserves organism timestep, neural topology and state, chemical state, motivation state, continuity history, and routing configuration across process restarts.

FragmentMemory remains external to the organism snapshot. The adapter preserves an attached memory object when restoring a snapshot; the application must reopen and attach the memory database.

Outcome-based Hebbian plasticity is computed on a candidate organism copy. VirtualBrain persists the proposed snapshot in mnn.plasticity_applied before the adapter commits it to the live organism. A resumed cycle restores the recorded snapshot instead of applying the same update twice.

The adapter's outcome_learning_rate controls this outcome-driven update. MNNOrganism.learning_rate remains separate and controls the organism's existing prediction-error-modulated plasticity during step.

## Validation

```bash
python -m unittest tests.test_mnn_organism_adapter -v
python -m unittest discover -s tests -v
```

Focused tests cover journal trace persistence, restart restoration, negative reward on failed actions, and input mapping validation.

## Limits

- Configured features are simple numeric proxies, not semantic representations.
- The base cognition engine still generates plans and Agency still makes decisions.
- The adapter does not establish that MNN activations understand observations.
- Persistent organism state and an autobiographical ledger do not establish subjective continuity or consciousness.
- The integration is opt-in. Existing users of MNNCognitionAdapter are unaffected.
