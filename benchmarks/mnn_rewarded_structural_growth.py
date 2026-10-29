"""Reward-gated structural growth inside the delayed-experience cycle.

A cue and a response are active together during a successful experience. The
experience cycle resolves the reward and then invokes a bounded growth policy,
creating a cue -> response edge. Evaluation provides only the cue. A failed
outcome is used as a control and must not create the edge.

This is a teacher-forced structural association, not evidence of autonomous
discovery, general learning, or intelligence.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from machina.mnn import MNN, Unit
from machina.mnn_experience import MNNExperienceCheckpointStore, MNNExperienceCycle
from machina.mnn_structure import ActivityGrowthPolicy


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


def _run_failed_control() -> float:
    cycle = MNNExperienceCycle(
        make_network(),
        learning_rate=0.1,
        growth_policy=make_policy(),
    )
    cycle.step({"cue": 1.0, "response": 1.0})
    result = cycle.resolve(-1.0)
    if result["grown_connections"]:
        raise AssertionError("a failed outcome must not grow connections")
    return _response_to_cue(cycle.network)


def _run_experiment(
    checkpoint_path: Path,
    *,
    baseline: float,
    failed_control: float,
) -> dict[str, Any]:
    cycle = MNNExperienceCycle(
        make_network(),
        learning_rate=0.1,
        growth_policy=make_policy(),
    )
    cycle.step({"cue": 1.0, "response": 1.0})
    store = MNNExperienceCheckpointStore(checkpoint_path)
    store.save(cycle)
    resumed = store.load()
    resolution = resumed.resolve(1.0)

    trained = _response_to_cue(MNN.from_snapshot(resumed.network.snapshot()))
    trained_weights = {
        edge_id: edge.weight for edge_id, edge in resumed.network.connections.items()
    }
    store.save(resumed)
    reloaded = store.load()
    restored = _response_to_cue(MNN.from_snapshot(reloaded.network.snapshot()))
    restored_weights = {
        edge_id: edge.weight for edge_id, edge in reloaded.network.connections.items()
    }
    grown = resolution["grown_connections"]
    passed = (
        baseline == 0.0
        and failed_control == 0.0
        and trained == 0.75
        and restored == 0.75
        and len(grown) == 1
        and grown[0]["source"] == "cue"
        and grown[0]["target"] == "response"
        and restored_weights == trained_weights
    )
    return {
        "benchmark": "mnn_rewarded_structural_growth",
        "version": 1,
        "baseline_response_to_cue": baseline,
        "failed_outcome_response_to_cue": failed_control,
        "grown_connections": grown,
        "trained_response_to_cue": trained,
        "restored_response_to_cue": restored,
        "trained_weights": trained_weights,
        "restored_weights": restored_weights,
        "weights_preserved": restored_weights == trained_weights,
        "passed": passed,
        "interpretation": (
            "A successful delayed outcome gates one bounded cue-to-response "
            "growth event. A failed outcome is a control that leaves the "
            "network unchanged. This is not autonomous discovery or broad "
            "generalization."
        ),
    }


def run_benchmark(
    *,
    checkpoint_path: str | Path | None = None,
) -> dict[str, Any]:
    baseline = _response_to_cue(MNN.from_snapshot(make_network().snapshot()))
    failed_control = _run_failed_control()
    if checkpoint_path is None:
        with tempfile.TemporaryDirectory() as directory:
            return _run_experiment(
                Path(directory) / "experience.json",
                baseline=baseline,
                failed_control=failed_control,
            )
    return _run_experiment(
        Path(checkpoint_path),
        baseline=baseline,
        failed_control=failed_control,
    )


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
