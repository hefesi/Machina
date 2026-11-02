"""Real MNN memory-pathway ablation for Phase 3 experiments.

Both conditions use the same network, task, event and preloaded episodic
archive. The treatment alone routes retrieved evidence into the dedicated
memory_context neural input. This isolates the explicit retrieval-to-network
pathway; it does not test semantic memory or consciousness.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from .chemical_signaling import ChemicalEvent
from .experiment_harness import ExperimentHarness, ExperimentSpec
from .fragment_memory import FragmentMemory
from .mnn import Connection, MNN, Unit
from .mnn_organism import MNNOrganism


def _new_network() -> MNN:
    network = MNN()
    network.add_unit(Unit("sensor", activation="identity"))
    network.add_unit(Unit("memory_context", activation="identity"))
    network.add_unit(Unit("integrator", activation="tanh"))
    network.add_connection(Connection("sensor-integrator", "sensor", "integrator", 0.4))
    network.add_connection(Connection("memory-integrator", "memory_context", "integrator", 0.6))
    return network


def run_memory_guidance_ablation(
    harness: ExperimentHarness,
    *,
    hypothesis_id: str,
    code_revision: str,
    observation: str,
    query: str,
    seed: int = 0,
) -> dict[str, Any]:
    """Compare identical MNN trials with the explicit memory route off/on."""
    if not isinstance(harness, ExperimentHarness):
        raise TypeError("harness must be an ExperimentHarness")
    for name, value in (
        ("hypothesis_id", hypothesis_id),
        ("code_revision", code_revision),
        ("observation", observation),
        ("query", query),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    records = {}
    conditions = (
        ("memory_path_off", False),
        ("memory_path_on", True),
    )
    for condition, enabled in conditions:
        spec = ExperimentSpec(
            experiment_id=f"{hypothesis_id}:{condition}:seed-{seed}",
            hypothesis_id=hypothesis_id,
            condition=condition,
            seed=seed,
            input_data={"observation": observation, "query": query, "sensor_input": 0.5},
            configuration={
                "memory_archive_present": True,
                "retrieval_to_neural_route_enabled": enabled,
                "network_topology": "sensor+memory_context->integrator",
            },
            code_revision=code_revision,
            budget={"organism_steps": 2, "memory_queries": 1},
        )

        def execute(_: ExperimentSpec) -> dict[str, Any]:
            with tempfile.TemporaryDirectory() as directory:
                memory = FragmentMemory(Path(directory) / "episodes.sqlite3")
                try:
                    memory.add(
                        content=observation,
                        kind="episode",
                        source_uri=f"machina://phase3/{hypothesis_id}/seed-{seed}/prior",
                        importance=1.0,
                        confidence=1.0,
                        tags=("phase3", "memory-ablation", "retrieval-evidence"),
                        metadata={"seed": seed, "hypothesis_id": hypothesis_id},
                        fragment_id=f"phase3-{hypothesis_id}-{seed}-prior",
                    )
                    organism = MNNOrganism(
                        f"phase3-{condition}-{seed}",
                        network=_new_network(),
                        memory=memory,
                    )
                    guidance = (
                        organism.prepare_memory_guidance(
                            query, target_unit="memory_context"
                        )
                        if enabled else None
                    )
                    organism.step(
                        {"sensor": 0.5},
                        ChemicalEvent(reward=0.4, novelty=0.2),
                        memory_guidance=guidance,
                    )
                    # MNN updates synchronously: the routed signal influences
                    # downstream units on the following tick, not retroactively.
                    result = organism.step(
                        {"sensor": 0.5},
                        ChemicalEvent(reward=0.4, novelty=0.2),
                    )
                    signal = guidance.signal if guidance is not None else 0.0
                    evidence_ids = list(guidance.evidence_ids) if guidance is not None else []
                    return {
                        "metrics": {
                            "integrator_activation": result.neural_state["integrator"],
                            "memory_signal": signal,
                            "retrieved_evidence_count": float(len(evidence_ids)),
                            "timestep": float(result.timestep),
                        },
                        "intervention": {
                            "memory_archive_present": True,
                            "retrieval_to_neural_route_enabled": enabled,
                            "evidence_ids": evidence_ids,
                            "evidence_scores": (
                                dict(guidance.evidence_scores) if guidance is not None else {}
                            ),
                        },
                        "runtime": {
                            "organism": type(organism).__name__,
                            "network": type(organism.network).__name__,
                            "memory": type(memory).__name__,
                        },
                    }
                finally:
                    memory.close()

        records[condition] = harness.run(spec, execute)

    comparison = harness.compare(
        records["memory_path_off"].spec["experiment_id"],
        records["memory_path_on"].spec["experiment_id"],
        "integrator_activation",
    )
    return {
        "hypothesis_id": hypothesis_id,
        "seed": seed,
        "trials": {
            condition: record.snapshot()
            for condition, record in records.items()
        },
        "comparison": comparison,
        "interpretation": "descriptive_mechanistic_ablation",
        "causal_scope": (
            "The explicit lexical retrieval signal is the only intended intervention; "
            "the result does not establish semantic understanding or consciousness."
        ),
    }
