"""Run registered experiments against a real VirtualBrain instance.

The caller constructs one brain per experimental condition. This adapter only
executes the normal cognitive cycle and records operational evidence; it does
not alter policy, infer consciousness, or own/close the supplied brain.
"""
from __future__ import annotations

from typing import Any

from .experiment_harness import ExperimentHarness, ExperimentSpec, TrialRecord


def run_virtual_brain_trial(
    harness: ExperimentHarness,
    spec: ExperimentSpec,
    brain: Any,
) -> TrialRecord:
    """Execute one registered trial through the actual VirtualBrain loop.

    Required spec.input_data keys: observation and objective.
    The supplied brain must already represent the condition declared in
    spec.configuration (for example, a baseline or an ablated configuration).
    Its concrete component classes are recorded so the condition is auditable.
    """
    if not isinstance(harness, ExperimentHarness):
        raise TypeError("harness must be an ExperimentHarness")
    if not isinstance(spec, ExperimentSpec):
        raise TypeError("spec must be an ExperimentSpec")
    if not callable(getattr(brain, "run_cycle", None)):
        raise TypeError("brain must expose run_cycle")
    if not callable(getattr(brain, "audit_cycle", None)):
        raise TypeError("brain must expose audit_cycle")

    input_data = dict(spec.input_data)
    missing = {"observation", "objective"} - set(input_data)
    if missing:
        raise ValueError(f"spec.input_data missing keys: {sorted(missing)}")

    def execute(_: ExperimentSpec) -> dict[str, Any]:
        result = brain.run_cycle(
            input_data["observation"],
            input_data["objective"],
        )
        audit = brain.audit_cycle(result.cycle_id)
        events = tuple(result.events)
        event_types = [event.event_type for event in events]
        action_results = [
            event.artifact.data.get("status")
            for event in events
            if event.event_type == "action.result"
        ]
        component_types = {
            name: type(getattr(brain, name)).__name__
            for name in ("cognition", "agency", "action_executor", "learning")
            if getattr(brain, name, None) is not None
        }
        metrics = {
            "cycle_completed": float(result.status == "completed"),
            "audit_valid": float(audit.valid),
            "event_count": float(len(events)),
            "memory_retrieval_events": float(event_types.count("memory.retrieved")),
            "causal_input_references": float(sum(
                len(event.artifact.input_refs) for event in events
            )),
            "action_succeeded": float(bool(action_results) and all(
                status == "succeeded" for status in action_results
            )),
        }
        return {
            "metrics": metrics,
            "cycle_id": result.cycle_id,
            "cycle_status": result.status,
            "audit_errors": list(audit.errors),
            "event_types": event_types,
            "action_statuses": action_results,
            "runtime_components": component_types,
            "condition": spec.condition,
            "configuration": dict(spec.configuration),
        }

    return harness.run(spec, execute)
