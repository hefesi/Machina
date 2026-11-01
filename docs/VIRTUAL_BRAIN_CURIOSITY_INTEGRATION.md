# Virtual Brain Curiosity Integration

## Configuration

Curiosity investigation persistence is opt-in. Supply a separate SQLite path
when constructing the brain:

```python
brain = VirtualBrain(
    "brain.sqlite",
    curiosity_investigation_path="curiosity.sqlite",
)
```

Without this path, the existing Virtual Brain behavior is unchanged and
curiosity lifecycle calls raise a clear `RuntimeError`.

## Journal-linked lifecycle

Use a cycle already created by `start_cycle()` or `run_cycle()`:

- `start_curiosity_investigation(cycle_id, investigation_id, ...)`
- `record_curiosity_evidence(cycle_id, investigation_id, ...)`
- `close_curiosity_investigation(cycle_id, investigation_id, ...)`

Each operation updates the SQLite investigation ledger and appends a
corresponding immutable event to the brain's hash-chained EventStore:

- `curiosity.investigation_started`
- `curiosity.evidence_recorded`
- `curiosity.investigation_closed`

The journal artifact uses the `curiosity_record` contract and carries the
investigation ID, operation and full record snapshot. Evidence references are
also preserved as artifact source references. This allows an auditor to trace
the investigation lifecycle alongside observations, goals, decisions and
experiences in the same brain cycle.

The curiosity SQLite database remains the lifecycle source of truth for
history queries; the EventStore is an append-only audit mirror. They are
separate SQLite databases, so this first integration does not claim a
cross-database atomic transaction. A process interruption between the ledger
commit and journal append can require reconciliation.

## Epistemic boundaries

- The caller still supplies the question, hypothesis, selection rationale,
  finding and evidence reference.
- A reference is provenance metadata, not independent verification.
- Curiosity records are marked `uncertain` in the brain journal.
- This integration records investigation continuity; it does not browse,
  conduct experiments, execute external actions, grant permissions, or
  automatically promote findings into beliefs.
- A durable journal and persistent self-reference are engineering mechanisms,
  not proof of subjective consciousness or metaphysical free will.
