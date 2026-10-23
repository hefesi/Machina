"""Measure MNN association retention, cue omission, and interference.

This is a controlled toy experiment. One association is trained, a separate
association is learned, and then the original association is deliberately
reversed. It measures behavior and persisted weights; it is not a model of
human forgetting or a test of consciousness.
"""
from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from typing import Any

from machina.mnn import Connection, MNN, Unit
from machina.mnn_checkpoint import MNNCheckpointStore


def make_network() -> MNN:
    network = MNN(weight_limit=5.0)
    network.add_unit(Unit("cue_a", activation="identity"))
    network.add_unit(Unit("cue_b", activation="identity"))
    network.add_unit(Unit("response", activation="identity"))
    network.add_connection(Connection("memory_a", "cue_a", "response", 0.0))
    network.add_connection(Connection("memory_b", "cue_b", "response", 0.0))
    return network


def _predict(network: MNN, cue_a: float, cue_b: float) -> float:
    network.reset_states()
    inputs = {"cue_a": cue_a, "cue_b": cue_b}
    network.step(inputs)
    return network.step(inputs)["response"]


def _train_association(
    network: MNN, *, cue: str, target: float, rounds: int, learning_rate: float
) -> None:
    for _ in range(rounds):
        network.reset_states()
        network.step({cue: 1.0, "response": target})
        network.apply_hebbian(learning_rate=learning_rate, reward=1.0)


def run_benchmark(
    *,
    checkpoint_path: str | Path | None = None,
    learning_rate: float = 0.25,
    initial_rounds: int = 4,
    unrelated_rounds: int = 4,
    interference_rounds: int = 12,
) -> dict[str, Any]:
    """Run retention, cue-omission, interference, and checkpoint probes."""
    if isinstance(learning_rate, bool) or not isinstance(learning_rate, (int, float)):
        raise ValueError("learning_rate must be a finite positive number")
    learning_rate = float(learning_rate)
    if not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError("learning_rate must be a finite positive number")
    for name, rounds in (
        ("initial_rounds", initial_rounds),
        ("unrelated_rounds", unrelated_rounds),
        ("interference_rounds", interference_rounds),
    ):
        if isinstance(rounds, bool) or not isinstance(rounds, int) or rounds <= 0:
            raise ValueError(f"{name} must be a positive integer")

    network = make_network()
    _train_association(
        network, cue="cue_a", target=1.0,
        rounds=initial_rounds, learning_rate=learning_rate,
    )
    initial_weight = network.connections["memory_a"].weight
    initial_output = _predict(network, 1.0, 0.0)

    # Learning an independent association should not change memory_a.
    _train_association(
        network, cue="cue_b", target=1.0,
        rounds=unrelated_rounds, learning_rate=learning_rate,
    )
    retained_weight = network.connections["memory_a"].weight
    retained_output = _predict(network, 1.0, 0.0)

    # No cue is supplied: a low response is not evidence that memory_a's
    # weight was erased. This deliberately separates cue availability from
    # the state of the stored association.
    omitted_cue_output = _predict(network, 0.0, 0.0)
    weight_before_interference = network.connections["memory_a"].weight

    # Repeatedly pair the same cue with the opposite target to create
    # controlled interference in the same connection.
    _train_association(
        network, cue="cue_a", target=-1.0,
        rounds=interference_rounds, learning_rate=learning_rate,
    )
    interfered_weight = network.connections["memory_a"].weight
    interfered_output = _predict(network, 1.0, 0.0)

    if checkpoint_path is None:
        with tempfile.TemporaryDirectory() as directory:
            store = MNNCheckpointStore(Path(directory) / "retention-checkpoint.json")
            store.save(network)
            restored = store.load()
    else:
        store = MNNCheckpointStore(checkpoint_path)
        store.save(network)
        restored = store.load()

    restored_weight = restored.connections["memory_a"].weight
    restored_output = _predict(restored, 1.0, 0.0)
    passed = (
        initial_weight > 0
        and initial_output > 0
        and retained_weight == initial_weight
        and retained_output == initial_output
        and omitted_cue_output == 0.0
        and weight_before_interference > 0
        and interfered_weight < 0
        and interfered_output < 0
        and restored_weight == interfered_weight
        and restored_output == interfered_output
    )
    return {
        "benchmark": "mnn_retention_interference",
        "version": 1,
        "parameters": {
            "learning_rate": learning_rate,
            "initial_rounds": initial_rounds,
            "unrelated_rounds": unrelated_rounds,
            "interference_rounds": interference_rounds,
        },
        "initial_learning": {
            "weight": initial_weight,
            "output_for_original_cue": initial_output,
            "retained": initial_output > 0,
        },
        "after_unrelated_learning": {
            "weight": retained_weight,
            "output_for_original_cue": retained_output,
            "retained": retained_output > 0,
            "weight_unchanged": retained_weight == initial_weight,
        },
        "cue_omission_probe": {
            "output_without_either_cue": omitted_cue_output,
            "original_association_weight_still_present": weight_before_interference > 0,
            "interpretation": (
                "A missing cue suppresses the response while the learned weight "
                "remains present; this is a controlled cue-availability probe, "
                "not proof of a human-like retrieval mechanism."
            ),
        },
        "after_conflicting_learning": {
            "weight": interfered_weight,
            "output_for_original_cue": interfered_output,
            "original_association_retained": interfered_output > 0,
            "behavior_changed": interfered_output < 0,
        },
        "after_checkpoint_restore": {
            "weight": restored_weight,
            "output_for_original_cue": restored_output,
            "weights_preserved": restored_weight == interfered_weight,
            "behavior_preserved": restored_output == interfered_output,
        },
        "passed": passed,
        "interpretation": (
            "In this toy network, an independent association does not damage "
            "the original edge, while repeated opposite supervision changes "
            "that edge and reverses the response. The checkpoint faithfully "
            "preserves the changed state. This demonstrates controlled "
            "interference, not general memory, human-like forgetting, or "
            "consciousness."
        ),
    }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
