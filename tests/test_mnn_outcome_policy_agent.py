"""End-to-end tests for contextual outcome policy integration."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent
from machina.mnn_contextual_outcome_policy import MNNContextualOutcomePolicy


class MNNOutcomePolicyAgentTests(unittest.TestCase):
    def add_outcome(self, memory, identifier, action, reward, context="stable morning"):
        memory.add(
            f"Observed {action} reward {reward} in {context}",
            kind="action-outcome",
            source_uri=f"test://{identifier}",
            confidence=1.0,
            tags=("action-learning", action),
            metadata={"action": action, "reward": reward, "context": context},
            fragment_id=identifier,
        )

    def test_policy_guides_agent_and_real_reward_is_archived(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            for index, reward in enumerate((0.1, 0.2)):
                self.add_outcome(memory, f"left-{index}", "left", reward)
            for index, reward in enumerate((0.8, 0.9)):
                self.add_outcome(memory, f"right-{index}", "right", reward)

            learner = MNNActionLearner(["left", "right"])
            policy = MNNContextualOutcomePolicy(memory, learner.actions, min_samples_per_action=2)
            agent = MNNLearningAgent(learner, memory, outcome_policy=policy)
            decision = agent.decide(context="stable morning", use_outcome_policy=True)

            self.assertEqual("right", decision["action"])
            self.assertEqual("outcome_policy", decision["selection_source"])
            self.assertEqual("recommended", decision["outcome_policy_result"]["status"])
            self.assertEqual(2, decision["outcome_policy_result"]["sample_counts"]["right"])

            resolved = agent.resolve(1.0, context="stable morning")
            observed = memory.get(resolved["experience_id"], record_access=False)
            self.assertEqual("right", observed.metadata["action"])
            self.assertEqual(1.0, observed.metadata["reward"])
            self.assertEqual("stable morning", observed.metadata["context"])

    def test_policy_abstention_falls_back_and_requests_more_experience(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            learner = MNNActionLearner(["left", "right"])
            policy = MNNContextualOutcomePolicy(memory, learner.actions, min_samples_per_action=2)
            agent = MNNLearningAgent(learner, memory, outcome_policy=policy)
            decision = agent.decide(context="new situation", use_outcome_policy=True)

            self.assertEqual("learner", decision["selection_source"])
            self.assertEqual("abstain", decision["outcome_policy_result"]["status"])
            self.assertTrue(decision["request_experience"])
            agent.resolve(0.0, context="new situation")

    def test_pending_policy_action_survives_snapshot_restore(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            for index, reward in enumerate((0.1, 0.2)):
                self.add_outcome(memory, f"left-{index}", "left", reward)
            for index, reward in enumerate((0.8, 0.9)):
                self.add_outcome(memory, f"right-{index}", "right", reward)

            learner = MNNActionLearner(["left", "right"])
            policy = MNNContextualOutcomePolicy(memory, learner.actions)
            agent = MNNLearningAgent(learner, memory, outcome_policy=policy)
            agent.decide(context="stable morning", use_outcome_policy=True)
            snapshot = json.loads(json.dumps(agent.snapshot()))

            restored = MNNLearningAgent.from_snapshot(snapshot, memory, outcome_policy=policy)
            self.assertEqual("right", restored.pending_action)
            self.assertEqual("outcome_policy", restored.pending_action_source)
            restored.resolve(0.7, context="stable morning")

    def test_invalid_policy_context_does_not_advance_learner(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            learner = MNNActionLearner(["left", "right"])
            policy = MNNContextualOutcomePolicy(memory, learner.actions)
            agent = MNNLearningAgent(learner, memory, outcome_policy=policy)
            with self.assertRaises(ValueError):
                agent.decide(use_outcome_policy=True)
            self.assertEqual(0, learner.decisions)

    def test_context_policy_requires_same_action_order_as_learner(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            policy = MNNContextualOutcomePolicy(memory, ["right", "left"])
            with self.assertRaises(ValueError):
                MNNLearningAgent(MNNActionLearner(["left", "right"]), memory, outcome_policy=policy)


if __name__ == "__main__":
    unittest.main()
