# Self-continuity and revisable commitments

## Motivation

A persistent identity model must preserve not only its current commitments but
also the path by which those commitments changed. Otherwise, revising a value
silently erases evidence of the previous state and makes continuity difficult
to audit.

## Current implementation

`SelfContinuity` now maintains:

- `commitments`: the currently active commitment values.
- `commitment_history`: append-only revisions with sequence, previous value,
  new value, reason, and source.
- `event_history`: the existing chronological event stream, including
  commitment changes and retirements.
- `component_versions`: the versions of the components participating in the
  functional identity.

`update_commitment()` requires a non-empty reason and source, rejects no-op
revisions, and records the previous and new values. `retire_commitment()`
removes a commitment from the active set but retains its final value in the
revision history. Retirement is not deletion of history.

Snapshots are JSON-compatible and detached from internal state.
`from_snapshot()` validates schema and sequence continuity. The continuity
report now checks whether both event and commitment histories extend a prior
snapshot.

## Example

```python
from machina.self_continuity import SelfContinuity

identity = SelfContinuity("machina-01")
identity.update_commitment(
    "protect_data", "Never delete archives without review",
    reason="initial safety baseline", source="bootstrap",
)
identity.update_commitment(
    "protect_data", "Preserve archives and require verified recovery",
    reason="revised after recovery experiment", source="cycle-12",
)
checkpoint = identity.snapshot()
restored = SelfContinuity.from_snapshot(checkpoint)
```

The active commitment contains the revised value; the history retains both
versions and why they changed.

## Important boundary

This is an auditable data structure, not an autonomous moral faculty. The
caller still decides when a commitment is revised and supplies the reason and
source. No automatic self-modification, permission escalation, or external
action is introduced. A future integration with the EventStore should make
commitment revisions part of the same durable causal journal as the cognitive
cycles, with explicit validation before a revision is committed.

Functional continuity across snapshots does not establish subjective identity,
consciousness, or metaphysical free will.
