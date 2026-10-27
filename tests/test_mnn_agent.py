import json
import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent


class MNNLearningAgentTests(unittest.TestCase):
    def test_decision_outcome_updates_policy_and_persists_experience(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            with FragmentMemory(path) as memory:
                agent = MNNLearningAgent(
                    MNNActionLearner(["left", "right"], learning_rate=0.5),
                    memory,
                )
                decision = agent.decide()
                result = agent.resolve(1.0, context="first controlled trial")
                self.assertEqual(result["learning_update"]["action"], decision["action"])
                self.assertEqual(result["experience_count"], 1)
                self.assertEqual(memory.count(), 1)
                recalled = agent.recall("controlled trial")
                self.assertEqual(len(recalled), 1)
                self.assertEqual(recalled[0].metadata["reward"], 1.0)

            with FragmentMemory(path) as reopened:
                self.assertEqual(reopened.count(), 1)
                self.assertTrue(reopened.recall("first controlled trial"))

    def test_requires_outcome_before_next_decision(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["a", "b"]), memory)
            agent.decide()
            with self.assertRaises(RuntimeError):
                agent.decide()
            with self.assertRaises(RuntimeError):
                MNNLearningAgent(MNNActionLearner(["a", "b"]), memory).resolve(1.0)

    def test_snapshot_restores_in_flight_decision(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["a", "b"]), memory)
            decision = agent.decide()
            snapshot = json.loads(json.dumps(agent.snapshot()))
            restored = MNNLearningAgent.from_snapshot(snapshot, memory)
            self.assertEqual(restored.pending_action, decision["action"])
            result = restored.resolve(0.8)
            self.assertEqual(result["experience_count"], 1)
            self.assertIsNone(restored.pending_action)

    def test_rejects_invalid_reward_without_clearing_pending_action(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["a", "b"]), memory)
            agent.decide()
            with self.assertRaises(ValueError):
                agent.resolve(float("nan"))
            self.assertIsNotNone(agent.pending_action)
            self.assertEqual(memory.count(), 0)

    def test_snapshot_rejects_mismatched_pending_action(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["a", "b"]), memory)
            agent.decide()
            snapshot = agent.snapshot()
            snapshot["pending_action"] = "not-an-action"
            with self.assertRaises(ValueError):
                MNNLearningAgent.from_snapshot(snapshot, memory)


if __name__ == "__main__":
    unittest.main()
