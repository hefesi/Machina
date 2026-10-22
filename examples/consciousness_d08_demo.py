"""D08 demo: Self/world state, continuity and operational relevance."""
from __future__ import annotations

import json

from machina.relevance import EventSignals, score_relevance
from machina.self_continuity import SelfContinuity
from machina.subjective_state import FunctionalSubjectiveState


def run_demo() -> dict[str, object]:
    state = FunctionalSubjectiveState(
        goals={"preserve_important_memory": 0.9},
        priorities={"data_loss": 0.95},
    )
    state.set_world_fact("storage_status", "healthy", "system_probe", 0.99)
    state.set_self_fact("persistent_memory_enabled", True, "configuration_check", 1.0)
    state.mark_unknown("future_outcome")
    state.add_memory("backup verified", source="test_run:001", importance=0.9)

    previous = SelfContinuity("machina-prototype", commitments={"backup": "enabled"}, component_versions={"mnn": "0.3"})
    previous.record_event("initialized", "runtime")
    current = SelfContinuity(
        "machina-prototype",
        commitments={"backup": "enabled"},
        event_history=list(previous.event_history),
        component_versions={"mnn": "0.3"},
    )
    current.record_event("backup_verified", "test_run:001", reason="probe succeeded")

    relevance = score_relevance(EventSignals(
        goal_alignment=1.0,
        novelty=0.6,
        future_decision_impact=0.9,
        urgency=0.8,
    ))
    report = current.continuity_report(previous)
    passed = (
        state.snapshot()["world"]["storage_status"]["value"] == "healthy"
        and state.snapshot()["self_model"]["persistent_memory_enabled"]["value"] is True
        and "future_outcome" in state.snapshot()["unknowns"]
        and report["same_agent_id"]
        and report["history_extends_previous"]
        and relevance > 0.0
    )
    return {
        "experiment": "d08_functional_subjectivity",
        "functional_state": state.snapshot(),
        "self_continuity": report,
        "event_relevance_score": relevance,
        "passed": passed,
        "interpretation": (
            "Validates data structures and deterministic functional relationships. "
            "It does not test or establish phenomenal consciousness."
        ),
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)
