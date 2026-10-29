"""Prune a grown edge after repeated negative outcomes.

A successful experience grows a bounded cue -> response edge. The same edge is
then exposed to consecutive failures. With a pruning threshold of two, the first
failure persists the edge with utility -1, and the second failure removes it.
A control cycle without pruning keeps the edge. The experiment is a narrow
resource-control test, not evidence of autonomous topology optimization.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from machina.mnn import MNN, Unit
from machina.mnn_experience import MNNExperienceCheckpointStore, MNNExperienceCycle
from machina.mnn_structure import ActivityGrowthPolicy

EDGE_ID = "grown:cue->response"


def make_network() -> MNN:
    network = MNN(weight_limit=2.0)
    network.add_unit(Unit("cue", activation="identity"))
    network.add_unit(Unit("response", activation="identity"))
    return network


def make_policy() -> ActivityGrowthPolicy:
    return ActivityGrowthPolicy(
        max_new_connections=1,
        initial_weight=0.75,
        min_activity=0.1,
        allowed_sources={"cue"},
        allowed_targets={"response"},
    )


def _response_to_cue(network: MNN) -> float:
    network.reset_states()
    network.step({"cue": 1.0})
    return network.step({"cue": 1.0})["response"]


def _make_cycle(*, prune_after_negative_outcomes: int | None) -> MNNExperienceCycle:
    return MNNExperienceCycle(
        make_network(),
        # Isolate structural maintenance from weight plasticity.
        learning_rate=0.0,
        growth_policy=make_policy(),
        prune_after_negative_outcomes=prune_after_negative_outcomes,
    )


def _step_and_resolve(cycle: MNNExperienceCycle, reward: float) -> dict:
    cycle.step({"cue": 1.0, "response": 1.0})
    return cycle.resolve(reward)


def _run_pruning(checkpoint_path: Path) -> dict[str, Any]:
    cycle = _make_cycle(prune_after_negative_outcomes=2)
    growth = _step_and_resolve(cycle, 1.0)
    after_growth = _response_to_cue(MNN.from_snapshot(cycle.network.snapshot()))
    first_failure = _step_and_resolve(cycle, -1.0)
    first_failure_response = _response_to_cue(
        MNN.from_snapshot(cycle.network.snapshot())
    )

    store = MNNExperienceCheckpointStore(checkpoint_path)
    store.save(cycle)
    resumed = store.load()
    utility_after_restart = dict(resumed.structural_utility)
    second_failure = _step_and_resolve(resumed, -1.0)
    after_pruning = _response_to_cue(MNN.from_snapshot(resumed.network.snapshot()))
    store.save(resumed)
    reopened = store.load()
    after_reload = _response_to_cue(MNN.from_snapshot(reopened.network.snapshot()))

    return {
        "grown_connections": growth["grown_connections"],
        "after_growth_response_to_cue": after_growth,
        "first_failure_pruned_connections": first_failure["pruned_connections"],
        "first_failure_response_to_cue": first_failure_response,
        "utility_after_restart": utility_after_restart,
        "second_failure_pruned_connections": second_failure["pruned_connections"],
        "after_pruning_response_to_cue": after_pruning,
        "after_reload_response_to_cue": after_reload,
        "edge_exists_after_reload": EDGE_ID in reopened.network.connections,
    }


def _run_control() -> dict[str, Any]:
    cycle = _make_cycle(prune_after_negative_outcomes=None)
    _step_and_resolve(cycle, 1.0)
    first_failure = _step_and_resolve(cycle, -1.0)
    second_failure = _step_and_resolve(cycle, -1.0)
    return {
        "first_failure_pruned_connections": first_failure["pruned_connections"],
        "second_failure_pruned_connections": second_failure["pruned_connections"],
        "control_response_to_cue": _response_to_cue(
            MNN.from_snapshot(cycle.network.snapshot())
        ),
        "control_edge_exists": EDGE_ID in cycle.network.connections,
    }


def run_benchmark(
    *,
    checkpoint_path: str | Path | None = None,
) -> dict[str, Any]:
    if checkpoint_path is None:
        with tempfile.TemporaryDirectory() as directory:
            pruning = _run_pruning(Path(directory) / "experience.json")
    else:
        pruning = _run_pruning(Path(checkpoint_path))
    control = _run_control()
    passed = (
        len(pruning["grown_connections"]) == 1
        and pruning["after_growth_response_to_cue"] == 0.75
        and pruning["first_failure_pruned_connections"] == []
        and pruning["first_failure_response_to_cue"] == 0.75
        and pruning["utility_after_restart"] == {EDGE_ID: -1}
        and pruning["second_failure_pruned_connections"] == [EDGE_ID]
        and pruning["after_pruning_response_to_cue"] == 0.0
        and pruning["after_reload_response_to_cue"] == 0.0
        and not pruning["edge_exists_after_reload"]
        and control["first_failure_pruned_connections"] == []
        and control["second_failure_pruned_connections"] == []
        and control["control_response_to_cue"] == 0.75
        and control["control_edge_exists"]
    )
    return {
        "benchmark": "mnn_grown_edge_pruning",
        "version": 1,
        "pruning_threshold": 2,
        "pruning": pruning,
        "control": control,
        "passed": passed,
        "interpretation": (
            "The grown edge is removed only after two consecutive negative "
            "outcomes, and its counter survives a checkpoint restart. The "
            "control shows that the same failures do not remove the edge when "
            "pruning is disabled. This is a bounded maintenance rule, not "
            "autonomous topology optimization or general intelligence."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
