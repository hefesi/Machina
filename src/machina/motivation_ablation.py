"""Paired motivation ablation for the real autonomy goal-selection policy.

The control and treatment use the same AutonomyController and context. Only
the treatment receives a persistent MotivationSystem. This tests whether
persistent drive pressure changes the policy's selected internal goal.
"""
from __future__ import annotations

from typing import Any

from .autonomy import AutonomyContext, AutonomyController
from .experiment_harness import ExperimentHarness, ExperimentSpec
from .mnn_motivation import MotivationSystem, MotivationalDrive


def run_motivation_ablation(
    harness: ExperimentHarness,
    *,
    hypothesis_id: str,
    code_revision: str,
    context: AutonomyContext | None = None,
    seed: int = 0,
    drive_name: str = "exploration",
    pressure: float = 0.95,
) -> dict[str, Any]:
    """Compare goal selection with the motivation pathway disabled/enabled."""
    if not isinstance(harness, ExperimentHarness):
        raise TypeError("harness must be an ExperimentHarness")
    for name, value in (("hypothesis_id", hypothesis_id), ("code_revision", code_revision)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    if not isinstance(drive_name, str) or not drive_name.strip():
        raise ValueError("drive_name must be a non-empty string")
    if isinstance(pressure, bool) or not isinstance(pressure, (int, float)) or not 0.0 <= pressure <= 1.0:
        raise ValueError("pressure must be between 0 and 1")
    selected_context = context or AutonomyContext()
    if not isinstance(selected_context, AutonomyContext):
        raise TypeError("context must be an AutonomyContext")

    context_data = {
        "memory_count": selected_context.memory_count,
        "important_memory_count": selected_context.important_memory_count,
        "unresolved_questions": selected_context.unresolved_questions,
        "failed_cycles": selected_context.failed_cycles,
        "cycles_since_reflection": selected_context.cycles_since_reflection,
        "cycles_since_memory_review": selected_context.cycles_since_memory_review,
    }
    records = {}
    for condition, enabled in (("motivation_off", False), ("motivation_on", True)):
        spec = ExperimentSpec(
            experiment_id=f"{hypothesis_id}:{condition}:seed-{seed}",
            hypothesis_id=hypothesis_id,
            condition=condition,
            seed=seed,
            input_data={"context": context_data, "drive_name": drive_name, "pressure": float(pressure)},
            configuration={"motivation_enabled": enabled, "policy": "bounded_utility_feedback_v2"},
            code_revision=code_revision,
            budget={"goal_generation": 1, "goal_selection": 1},
        )

        def execute(_: ExperimentSpec) -> dict[str, Any]:
            motivation = None
            if enabled:
                motivation = MotivationSystem([
                    MotivationalDrive(
                        name=drive_name,
                        level=float(pressure),
                        setpoint=float(pressure),
                        priority=1.0,
                        recovery_rate=0.0,
                        persistence=0.0,
                        pressure=float(pressure),
                    )
                ])
            decision = AutonomyController().step(selected_context, motivation=motivation)
            chosen = decision.selected_goal
            if chosen is None:
                raise RuntimeError("autonomy policy did not select an internal goal")
            is_motivational = chosen.goal_id == f"sustain_drive:{drive_name}"
            return {
                "metrics": {
                    "motivational_goal_selected": float(is_motivational),
                    "selected_goal_urgency": float(chosen.urgency),
                    "candidate_count": float(len(decision.alternatives)),
                },
                "decision": decision.to_dict(),
                "intervention": {
                    "motivation_enabled": enabled,
                    "drive_name": drive_name if enabled else None,
                    "drive_pressure": float(pressure) if enabled else None,
                },
                "runtime": {
                    "controller": "AutonomyController",
                    "motivation": type(motivation).__name__ if motivation is not None else None,
                },
            }

        records[condition] = harness.run(spec, execute)

    comparison = harness.compare(
        records["motivation_off"].spec["experiment_id"],
        records["motivation_on"].spec["experiment_id"],
        "motivational_goal_selected",
    )
    return {
        "hypothesis_id": hypothesis_id,
        "seed": seed,
        "trials": {name: record.snapshot() for name, record in records.items()},
        "comparison": comparison,
        "interpretation": "descriptive_mechanistic_ablation",
        "causal_scope": (
            "Tests whether a persistent motivational pressure signal changes "
            "the selected internal goal under this policy and context; it does "
            "not establish subjective desire, agency or free will."
        ),
    }
