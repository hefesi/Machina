"""Measure action learning, adaptation after a reward shift, and durable restart.

Run from the repository root:
    python -m benchmarks.mnn_persistent_adaptation

This controlled two-action task is a small engineering benchmark, not a claim
of general intelligence, semantic understanding, or subjective experience.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner


def _phase(learner: MNNActionLearner, *, preferred: str, rounds: int) -> dict[str, Any]:
    rewards: list[float] = []
    actions: list[str] = []
    for _ in range(rounds):
        action = learner.choose()
        reward = 1.0 if action == preferred else 0.0
        learner.observe(reward)
        actions.append(action)
        rewards.append(reward)
    tail = rewards[-min(10, len(rewards)):]
    return {
        "preferred_action": preferred,
        "rounds": rounds,
        "total_reward": sum(rewards),
        "reward_rate": sum(rewards) / len(rewards),
        "last_10_reward_rate": sum(tail) / len(tail),
        "action_counts": {name: actions.count(name) for name in learner.actions},
        "predictions": learner.predictions(),
    }


def run_benchmark(
    *,
    state_path: str | Path | None = None,
    memory_path: str | Path | None = None,
    rounds_per_phase: int = 40,
) -> dict[str, Any]:
    """Learn a reward mapping, restart from disk, then adapt to a reversed mapping."""
    if isinstance(rounds_per_phase, bool) or not isinstance(rounds_per_phase, int) or rounds_per_phase < 10:
        raise ValueError("rounds_per_phase must be an integer of at least 10")

    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        durable_state = Path(state_path) if state_path is not None else root / "learner-state.json"
        durable_memory = Path(memory_path) if memory_path is not None else root / "experience.sqlite3"
        durable_state.parent.mkdir(parents=True, exist_ok=True)
        durable_memory.parent.mkdir(parents=True, exist_ok=True)

        learner = MNNActionLearner(
            ["left", "right"], learning_rate=0.35, exploration_interval=3
        )
        first_phase = _phase(learner, preferred="left", rounds=rounds_per_phase)
        state_before_restart = learner.snapshot()
        predictions_before_restart = learner.predictions()
        durable_state.write_text(
            json.dumps(state_before_restart, sort_keys=True, allow_nan=False),
            encoding="utf-8",
        )

        with FragmentMemory(durable_memory) as memory:
            memory.add(
                "The first environment phase rewarded the left action.",
                kind="experience",
                source_uri="benchmark://persistent-adaptation/phase-1",
                importance=0.7,
                confidence=1.0,
                tags=["action-learning", "phase-1", "left"],
                metadata={"preferred_action": "left", "rounds": rounds_per_phase},
            )
            memory.add(
                "The reward mapping changed: the right action is now rewarded.",
                kind="environment-change",
                source_uri="benchmark://persistent-adaptation/phase-2",
                importance=1.0,
                confidence=1.0,
                pinned=True,
                tags=["action-learning", "environment-shift", "right"],
                metadata={"previous_preference": "left", "new_preference": "right"},
            )

        restored = MNNActionLearner.from_snapshot(
            json.loads(durable_state.read_text(encoding="utf-8"))
        )
        restart_preserved_state = restored.snapshot() == state_before_restart
        predictions_after_restart = restored.predictions()
        second_phase = _phase(restored, preferred="right", rounds=rounds_per_phase)

        # Reopen SQLite to verify that experience survives closing and reopening.
        with FragmentMemory(durable_memory) as reopened_memory:
            archived = reopened_memory.archive()
            recalled = reopened_memory.recall("environment reward mapping changed right action")
            memory_persisted = len(archived) == 2 and any(
                "reward mapping changed" in item.content for item in recalled
            )

        passed = (
            first_phase["last_10_reward_rate"] >= 0.8
            and second_phase["last_10_reward_rate"] >= 0.8
            and first_phase["predictions"]["left"] > first_phase["predictions"]["right"]
            and second_phase["predictions"]["right"] > second_phase["predictions"]["left"]
            and restart_preserved_state
            and memory_persisted
        )
        return {
            "benchmark": "mnn_persistent_adaptation",
            "version": 1,
            "rounds_per_phase": rounds_per_phase,
            "phase_1": first_phase,
            "restart": {
                "learner_state_preserved": restart_preserved_state,
                "predictions_before_restart": predictions_before_restart,
                "predictions_after_restart": predictions_after_restart,
            },
            "phase_2": second_phase,
            "persistent_memory": {
                "archive_count_after_reopen": len(archived),
                "environment_shift_recalled": memory_persisted,
            },
            "passed": passed,
            "interpretation": (
                "The learner tracks a simple action-to-reward mapping, retains its "
                "numeric state after a JSON restart, and adapts when the mapping flips. "
                "SQLite retains an explicit environment-change memory. This does not "
                "test broad transfer, semantic reasoning, consciousness, or real-world "
                "autonomy."
            ),
        }


def main() -> None:
    result = run_benchmark()
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
