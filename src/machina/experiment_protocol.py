"""Paired, multi-seed protocol for real VirtualBrain conditions.

This module orchestrates trials; it deliberately does not pretend to know how
to disable arbitrary mechanisms. The caller must build each condition through
brain_factory, and the adapter records the concrete runtime component classes.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from .brain import VirtualBrain
from .experiment_harness import ExperimentHarness, ExperimentSpec
from .virtual_brain_experiment import run_virtual_brain_trial


BrainFactory = Callable[[str, int, Mapping[str, Any]], VirtualBrain]


def run_paired_conditions(
    *,
    harness: ExperimentHarness,
    hypothesis_id: str,
    baseline_condition: str,
    treatment_condition: str,
    seeds: Sequence[int],
    input_data: Mapping[str, Any],
    baseline_configuration: Mapping[str, Any],
    treatment_configuration: Mapping[str, Any],
    code_revision: str,
    budget: Mapping[str, int],
    brain_factory: BrainFactory,
    metrics: Sequence[str],
) -> dict[str, Any]:
    """Run baseline/treatment with identical inputs, seeds and declared budget.

    Each factory call must return a fresh VirtualBrain configured for exactly
    the requested condition. One database-backed brain is closed after each
    trial, including on exceptions. Trial IDs are deterministic and therefore
    safe to retry with the same specification.
    """
    if not isinstance(harness, ExperimentHarness):
        raise TypeError("harness must be an ExperimentHarness")
    if not callable(brain_factory):
        raise TypeError("brain_factory must be callable")
    for name, value in (
        ("hypothesis_id", hypothesis_id),
        ("baseline_condition", baseline_condition),
        ("treatment_condition", treatment_condition),
        ("code_revision", code_revision),
    ):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    if baseline_condition == treatment_condition:
        raise ValueError("baseline and treatment conditions must differ")
    if not seeds:
        raise ValueError("at least one seed is required")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be unique")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise ValueError("all seeds must be integers")
    if not isinstance(input_data, Mapping) or not {"observation", "objective"} <= set(input_data):
        raise ValueError("input_data must contain observation and objective")
    if not isinstance(budget, Mapping) or budget.get("cycles") != 1:
        raise ValueError("VirtualBrain adapter requires a declared cycles=1 budget")
    if not metrics or any(not isinstance(metric, str) or not metric.strip() for metric in metrics):
        raise ValueError("at least one non-empty metric name is required")

    configurations = {
        baseline_condition: dict(baseline_configuration),
        treatment_condition: dict(treatment_configuration),
    }
    trials: dict[str, list[str]] = {
        baseline_condition: [],
        treatment_condition: [],
    }

    for seed in seeds:
        for condition in (baseline_condition, treatment_condition):
            configuration = configurations[condition]
            brain = brain_factory(condition, seed, configuration)
            if not isinstance(brain, VirtualBrain):
                raise TypeError("brain_factory must return a VirtualBrain instance")
            try:
                spec = ExperimentSpec(
                    experiment_id=f"{hypothesis_id}:{condition}:seed-{seed}",
                    hypothesis_id=hypothesis_id,
                    condition=condition,
                    seed=seed,
                    input_data=dict(input_data),
                    configuration=configuration,
                    code_revision=code_revision,
                    budget=dict(budget),
                )
                record = run_virtual_brain_trial(harness, spec, brain)
                trials[condition].append(record.spec["experiment_id"])
            finally:
                brain.close()

    comparisons = []
    for seed in seeds:
        baseline_id = f"{hypothesis_id}:{baseline_condition}:seed-{seed}"
        treatment_id = f"{hypothesis_id}:{treatment_condition}:seed-{seed}"
        for metric in metrics:
            comparisons.append(
                harness.compare(baseline_id, treatment_id, metric)
            )

    return {
        "hypothesis_id": hypothesis_id,
        "seeds": list(seeds),
        "conditions": {
            baseline_condition: {
                "configuration": configurations[baseline_condition],
                "trial_ids": trials[baseline_condition],
            },
            treatment_condition: {
                "configuration": configurations[treatment_condition],
                "trial_ids": trials[treatment_condition],
            },
        },
        "comparisons": comparisons,
        "interpretation": "descriptive_only",
        "ablation_validity": (
            "The protocol verifies trial pairing and records runtime component "
            "classes; researchers must independently verify that each factory "
            "configuration implements the intended mechanism intervention."
        ),
    }
