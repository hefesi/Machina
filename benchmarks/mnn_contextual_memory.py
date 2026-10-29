"""Controlled comparison: context-free policy vs memory-assisted decisions.

Run with: python benchmarks/mnn_contextual_memory.py
This is a deterministic toy environment, not evidence of general intelligence.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent


ACTIONS = ("left", "right")
CONTEXTS = ("quiet morning", "busy evening")
TRIALS = 100


def seed_experience(memory: FragmentMemory) -> None:
    records = (
        ("left", 1.0, "quiet morning"),
        ("right", 0.0, "quiet morning"),
        ("left", 0.0, "busy evening"),
        ("right", 1.0, "busy evening"),
    )
    for index, (action, reward, context) in enumerate(records):
        memory.add(
            f"Action '{action}' received reward {reward:g}. Context: {context}",
            kind="action-outcome",
            source_uri=f"benchmark://seed/{index}",
            importance=0.8,
            confidence=1.0,
            tags=("action-learning", action),
            metadata={"action": action, "reward": reward, "context": context},
        )


def run_policy(use_memory: bool, database: Path) -> dict:
    with FragmentMemory(database) as memory:
        seed_experience(memory)
        agent = MNNLearningAgent(
            MNNActionLearner(list(ACTIONS), learning_rate=0.2, exploration_interval=7),
            memory,
            agent_id="contextual-benchmark",
        )
        total_reward = 0.0
        correct = 0
        memory_selections = 0
        for index in range(TRIALS):
            context = CONTEXTS[index % len(CONTEXTS)]
            target = "left" if context == "quiet morning" else "right"
            decision = agent.decide(context=context, use_memory=use_memory)
            reward = 1.0 if decision["action"] == target else 0.0
            agent.resolve(reward, context=context)
            total_reward += reward
            correct += int(decision["action"] == target)
            memory_selections += int(decision["selection_source"] == "memory")
        return {
            "policy": "memory-assisted" if use_memory else "context-free baseline",
            "trials": TRIALS,
            "reward_total": total_reward,
            "accuracy": correct / TRIALS,
            "memory_selected_actions": memory_selections,
        }


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        baseline = run_policy(False, root / "baseline.sqlite3")
        assisted = run_policy(True, root / "memory.sqlite3")
    result = {
        "task": "two contexts with opposite optimal actions",
        "note": "synthetic deterministic benchmark; lexical retrieval; seeded experience supplied",
        "results": [baseline, assisted],
        "accuracy_delta": assisted["accuracy"] - baseline["accuracy"],
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
