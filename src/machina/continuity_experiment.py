"""Controlled interruption/resumption experiment for VirtualBrain continuity.

This measures durable functional continuity across a process-style restart. It
does not assert persistence of subjective experience.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .brain import VirtualBrain
from .experiment_harness import ExperimentHarness, ExperimentSpec, TrialRecord


def run_interruption_resume_trial(
    harness: ExperimentHarness,
    spec: ExperimentSpec,
    storage_path: str | Path,
    *,
    checkpoint: str = "workspace.updated",
) -> TrialRecord:
    """Pause a real cycle at a durable checkpoint, reopen SQLite, then resume."""
    if not isinstance(harness, ExperimentHarness):
        raise TypeError("harness must be an ExperimentHarness")
    if not isinstance(spec, ExperimentSpec):
        raise TypeError("spec must be an ExperimentSpec")
    if not isinstance(checkpoint, str) or not checkpoint.strip():
        raise ValueError("checkpoint must be a non-empty event type")
    data = dict(spec.input_data)
    missing = {"observation", "objective"} - set(data)
    if missing:
        raise ValueError(f"spec.input_data missing keys: {sorted(missing)}")
    path = Path(storage_path)

    def execute(_: ExperimentSpec) -> dict[str, Any]:
        first = VirtualBrain(path)
        try:
            cycle_id = first.start_cycle(data["observation"], data["objective"])
            paused = first.advance(cycle_id, stop_after=checkpoint)
            if paused is not None:
                raise RuntimeError("expected cycle to pause at the requested checkpoint")
            events_before_restart = first.store.events_for_cycle(cycle_id)
            if not events_before_restart or events_before_restart[-1].event_type != checkpoint:
                raise RuntimeError("requested checkpoint was not durably reached")
            if first.store.latest_artifact(cycle_id, "cycle.completed") is not None:
                raise RuntimeError("cycle unexpectedly completed before restart")
            first.store.verify_integrity()
            event_count_before_restart = len(events_before_restart)
        finally:
            first.close()

        resumed = VirtualBrain(path)
        try:
            result = resumed.advance(cycle_id)
            if result is None:
                raise RuntimeError("resumed cycle did not reach a terminal state")
            audit = resumed.audit_cycle(cycle_id)
            resumed.store.verify_integrity()
            event_types = [event.event_type for event in result.events]
            completed_count = event_types.count("cycle.completed")
            return {
                "metrics": {
                    "checkpoint_reached": 1.0,
                    "events_persisted_before_restart": float(event_count_before_restart),
                    "audit_valid": float(audit.valid),
                    "cycle_completed": float(result.status == "completed"),
                    "completion_event_exactly_once": float(completed_count == 1),
                    "event_count_after_resume": float(len(result.events)),
                },
                "cycle_id": cycle_id,
                "checkpoint": checkpoint,
                "event_types": event_types,
                "audit_errors": list(audit.errors),
                "completion_event_count": completed_count,
                "integrity_verified": True,
                "interpretation": "functional_continuity_only",
            }
        finally:
            resumed.close()

    return harness.run(spec, execute)
