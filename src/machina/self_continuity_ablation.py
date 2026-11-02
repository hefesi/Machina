"""Self-continuity/commitment alignment ablation for autonomy selection.

Both conditions preserve the same SelfContinuity record and evaluate the same
candidate goals. The treatment exposes an independently declared,
evidence-grounded commitment-alignment signal to the existing policy; the
control withholds that signal. This tests functional policy sensitivity to
persistent commitments, not subjective identity.
"""
from __future__ import annotations

from typing import Any

from .autonomy import AutonomyController, GoalCandidate
from .experiment_harness import ExperimentHarness, ExperimentSpec
from .self_continuity import SelfContinuity


def run_commitment_alignment_ablation(
    harness: ExperimentHarness,
    *,
    hypothesis_id: str,
    code_revision: str,
    seed: int = 0,
) -> dict[str, Any]:
    if not isinstance(harness, ExperimentHarness):
        raise TypeError("harness must be an ExperimentHarness")
    for name, value in (("hypothesis_id", hypothesis_id), ("code_revision", code_revision)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")

    continuity = SelfContinuity(
        agent_id=f"machina-phase3-seed-{seed}",
        commitments={"evidence_integrity": "Preserve source traceability in conclusions."},
        component_versions={"autonomy": "bounded_utility_feedback_v2"},
    )
    candidates = [
        GoalCandidate(
            goal_id="goal_a",
            description="Investigate a new hypothesis",
            drive="curiosity",
            urgency=0.7,
            expected_benefit=0.7,
            confidence=0.8,
            estimated_cost=0.2,
            risk=0.05,
        ),
        GoalCandidate(
            goal_id="goal_b",
            description="Audit evidence provenance before concluding",
            drive="verification",
            urgency=0.7,
            expected_benefit=0.7,
            confidence=0.8,
            estimated_cost=0.2,
            risk=0.05,
        ),
    ]
    records = {}
    for condition, enabled in (("commitment_signal_off", False), ("commitment_signal_on", True)):
        spec = ExperimentSpec(
            experiment_id=f"{hypothesis_id}:{condition}:seed-{seed}",
            hypothesis_id=hypothesis_id,
            condition=condition,
            seed=seed,
            input_data={
                "commitments": continuity.commitments,
                "candidate_ids": [item.goal_id for item in candidates],
                "alignment_evidence": {"goal_b": "candidate directly operationalizes evidence_integrity"},
            },
            configuration={
                "commitment_alignment_enabled": enabled,
                "commitment_weight": 0.10,
                "policy": "bounded_utility_feedback_v2",
            },
            code_revision=code_revision,
            budget={"candidate_count": 2, "selection_calls": 1},
        )

        def execute(_: ExperimentSpec) -> dict[str, Any]:
            # Alignment is an explicit evaluator input, not inferred from text
            # by the controller. The ablation only toggles whether it is used.
            alignment = {"goal_b": 1.0} if enabled else {}
            decision = AutonomyController().choose(
                candidates,
                commitment_alignment=alignment,
                commitment_weight=0.10,
            )
            chosen = decision.selected_goal
            if chosen is None:
                raise RuntimeError("autonomy policy did not select a candidate")
            return {
                "metrics": {
                    "commitment_aligned_goal_selected": float(chosen.goal_id == "goal_b"),
                    "selected_goal_score": next(
                        float(item["score"]["total"])
                        for item in decision.alternatives
                        if item["goal"]["goal_id"] == chosen.goal_id
                    ),
                },
                "decision": decision.to_dict(),
                "continuity": continuity.snapshot(),
                "intervention": {
                    "commitment_alignment_enabled": enabled,
                    "alignment_evidence": {"goal_b": "candidate directly operationalizes evidence_integrity"},
                },
            }

        records[condition] = harness.run(spec, execute)

    comparison = harness.compare(
        records["commitment_signal_off"].spec["experiment_id"],
        records["commitment_signal_on"].spec["experiment_id"],
        "commitment_aligned_goal_selected",
    )
    return {
        "hypothesis_id": hypothesis_id,
        "seed": seed,
        "trials": {name: record.snapshot() for name, record in records.items()},
        "comparison": comparison,
        "interpretation": "descriptive_mechanistic_ablation",
        "causal_scope": (
            "Tests whether explicit commitment-alignment feedback changes "
            "functional goal selection. Alignment is supplied by an external "
            "evidence-aware evaluator; this does not establish a persistent "
            "subjective self or conscious identity."
        ),
    }
