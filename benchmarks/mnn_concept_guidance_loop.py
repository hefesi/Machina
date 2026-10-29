"""Compare a context-free learner with explicit concept-guided decisions.

Run with: python benchmarks/mnn_concept_guidance_loop.py
The synthetic environment has known rewards by context and action. Its concept
mapping is supplied by the application, so results test integration mechanics,
not autonomous discovery of action semantics or generalization.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent
from machina.mnn_concept_advisor import MNNConceptAdvisor
from machina.mnn_concepts import MNNConceptBuilder


ACTIONS = ("continue", "pause")
EPISODES = 40


def reward_for(context: str, action: str) -> float:
    if context == "stable-context":
        return 1.0 if action == "continue" else 0.0
    return 1.0 if action == "pause" else -1.0


def seed_evidence(memory: FragmentMemory) -> None:
    for tag in ("stable-context", "risk-context"):
        for index in range(2):
            identifier = f"{tag}-{index}"
            memory.add(
                f"Synthetic evidence for {tag} {index}",
                kind="fact", source_uri=f"benchmark://{identifier}",
                tags=(tag,), confidence=0.9,
                metadata={"polarity": "supports"}, fragment_id=identifier,
            )
    MNNConceptBuilder(memory, min_support=2).consolidate()


def run_policy(memory: FragmentMemory, *, guided: bool) -> dict:
    advisor = (
        MNNConceptAdvisor(memory, {
            "stable-context": "continue",
            "risk-context": "pause",
        }, min_support=2)
        if guided else None
    )
    agent = MNNLearningAgent(
        MNNActionLearner(list(ACTIONS), learning_rate=0.2, exploration_interval=5),
        memory, agent_id="guided" if guided else "baseline",
        concept_advisor=advisor,
    )
    total = 0.0
    correct = 0
    decisions = []
    for index in range(EPISODES):
        context = "stable-context" if index % 2 == 0 else "risk-context"
        decision = agent.decide(
            use_concepts=guided,
            context_tags=[context] if guided else None,
            context=context,
        )
        reward = reward_for(context, decision["action"])
        result = agent.resolve(reward, context=context)
        total += reward
        correct += int(reward == 1.0)
        decisions.append({
            "context": context,
            "action": decision["action"],
            "reward": reward,
            "selection_source": decision["selection_source"],
            "prediction_after": result["predictions"][decision["action"]],
        })
    return {
        "total_reward": total,
        "mean_reward": total / EPISODES,
        "optimal_action_rate": correct / EPISODES,
        "episodes": EPISODES,
        "decisions": decisions,
    }


def run() -> dict:
    with tempfile.TemporaryDirectory() as directory:
        with FragmentMemory(Path(directory) / "loop.sqlite3") as memory:
            seed_evidence(memory)
            baseline = run_policy(memory, guided=False)
            guided = run_policy(memory, guided=True)
            return {
                "benchmark": "mnn-concept-guidance-loop",
                "environment": "synthetic deterministic rewards, alternating contexts",
                "limitations": [
                    "action mappings are supplied, not learned",
                    "tags are explicit and not inferred from natural language",
                    "results do not establish generalization or causal understanding",
                ],
                "baseline": {key: value for key, value in baseline.items() if key != "decisions"},
                "concept_guided": {key: value for key, value in guided.items() if key != "decisions"},
                "reward_difference_guided_minus_baseline": guided["total_reward"] - baseline["total_reward"],
            }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
