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

    def test_memory_recommendation_distinguishes_contexts(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            # Store explicit context-action outcomes independent of global action values.
            memory.add(
                "Action 'left' received reward 1. Context: quiet morning",
                kind="action-outcome", source_uri="test://quiet-left",
                metadata={"action": "left", "reward": 1.0, "context": "quiet morning"},
                confidence=1.0, tags=("left",),
            )
            memory.add(
                "Action 'right' received reward 0. Context: quiet morning",
                kind="action-outcome", source_uri="test://quiet-right",
                metadata={"action": "right", "reward": 0.0, "context": "quiet morning"},
                confidence=1.0, tags=("right",),
            )
            memory.add(
                "Action 'left' received reward 0. Context: busy evening",
                kind="action-outcome", source_uri="test://busy-left",
                metadata={"action": "left", "reward": 0.0, "context": "busy evening"},
                confidence=1.0, tags=("left",),
            )
            memory.add(
                "Action 'right' received reward 1. Context: busy evening",
                kind="action-outcome", source_uri="test://busy-right",
                metadata={"action": "right", "reward": 1.0, "context": "busy evening"},
                confidence=1.0, tags=("right",),
            )

            quiet = agent.recommend_from_memory("quiet morning")
            busy = agent.recommend_from_memory("busy evening")
            self.assertEqual(quiet["action"], "left")
            self.assertEqual(busy["action"], "right")
            self.assertEqual(quiet["estimated_reward"], 1.0)
            self.assertEqual(busy["estimated_reward"], 1.0)
            self.assertTrue(quiet["evidence_ids"])
            # Recommendation is deliberately read-only: it must not train the learner.
            self.assertEqual(agent.learner.decisions, 0)
            self.assertEqual(agent.learner.predictions(), {"left": 0.0, "right": 0.0})

    def test_decide_can_use_contextual_memory_and_reports_fallback(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            memory.add(
                "Action 'right' received reward 1. Context: busy evening",
                kind="action-outcome", source_uri="test://busy-right",
                metadata={"action": "right", "reward": 1.0, "context": "busy evening"},
                confidence=1.0, tags=("right",),
            )
            decision = agent.decide(context="busy evening", use_memory=True)
            self.assertEqual(decision["action"], "right")
            self.assertEqual(decision["selection_source"], "memory")
            self.assertEqual(decision["fallback_action"], "left")
            self.assertTrue(decision["memory_recommendation"]["evidence_ids"])
            self.assertEqual(decision["memory_status"], "recommended")
            self.assertFalse(decision["request_experience"])
            agent.resolve(1.0, context="busy evening")

    def test_decide_memory_mode_falls_back_without_evidence(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            decision = agent.decide(context="unseen setting", use_memory=True)
            self.assertEqual(decision["selection_source"], "learner")
            self.assertEqual(decision["action"], decision["fallback_action"])
            self.assertEqual(decision["memory_status"], "no_recommendation")
            self.assertEqual(
                decision["fallback_reason"],
                "no_matching_or_unambiguous_memory_evidence",
            )
            self.assertTrue(decision["request_experience"])
            agent.resolve(0.0, context="unseen setting")

    def test_decide_exposes_epsilon_greedy_policy(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(
                MNNActionLearner(["left", "right"], exploration_seed=3), memory
            )
            decision = agent.decide(exploration_epsilon=1.0)
            self.assertEqual(decision["exploration_policy"], "epsilon_greedy")
            self.assertEqual(decision["exploration_epsilon"], 1.0)
            self.assertIn(decision["action"], ("left", "right"))
            agent.resolve(0.0)

    def test_decide_reports_scheduled_policy_by_default(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            decision = agent.decide()
            self.assertEqual(decision["exploration_policy"], "scheduled")
            self.assertIsNone(decision["exploration_epsilon"])
            agent.resolve(0.0)

    def test_decide_requires_context_for_memory_mode(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            with self.assertRaises(ValueError):
                agent.decide(use_memory=True)

    def test_memory_recommendation_abstains_on_conflicting_context_evidence(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            records = (
                ("left", 1.0, "noisy room"),
                ("right", 0.0, "noisy room"),
                ("left", 0.0, "noisy room"),
                ("right", 1.0, "noisy room"),
            )
            for index, (action, reward, context) in enumerate(records):
                memory.add(
                    f"Action '{action}' received reward {reward:g}. Context: {context}",
                    kind="action-outcome", source_uri=f"test://conflict-{index}",
                    metadata={"action": action, "reward": reward, "context": context},
                    confidence=1.0, tags=(action,),
                )

            self.assertIsNone(agent.recommend_from_memory("noisy room"))
            # A caller can request a stricter margin; the threshold is validated.
            with self.assertRaises(ValueError):
                agent.recommend_from_memory("noisy room", min_reward_margin=-0.1)

    def test_memory_recommendation_reports_evidence_and_margin(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            for index, (action, reward) in enumerate((("left", 1.0), ("right", 0.0))):
                memory.add(
                    f"Action '{action}' received reward {reward:g}. Context: quiet morning",
                    kind="action-outcome", source_uri=f"test://evidence-{index}",
                    metadata={"action": action, "reward": reward, "context": "quiet morning"},
                    confidence=1.0, tags=(action,),
                )
            recommendation = agent.recommend_from_memory("quiet morning")
            self.assertEqual(recommendation["action"], "left")
            self.assertEqual(recommendation["evidence_counts"], {"left": 1, "right": 1})
            self.assertEqual(recommendation["decision_margin"], 1.0)

    def test_memory_recommendation_returns_none_without_matching_context(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["a", "b"]), memory)
            self.assertIsNone(agent.recommend_from_memory("unseen context"))

    def test_memory_recommendation_rejects_empty_context(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["a", "b"]), memory)
            with self.assertRaises(ValueError):
                agent.recommend_from_memory(" ")

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

    def test_snapshot_restores_memory_overridden_pending_action(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            memory.add(
                "Action 'right' received reward 1. Context: busy evening",
                kind="action-outcome", source_uri="test://busy-right",
                metadata={"action": "right", "reward": 1.0, "context": "busy evening"},
                confidence=1.0, tags=("right",),
            )

            decision = agent.decide(context="busy evening", use_memory=True)
            self.assertEqual(decision["action"], "right")
            self.assertEqual(decision["fallback_action"], "left")
            self.assertEqual(agent.snapshot()["pending_action_source"], "memory")

            snapshot = json.loads(json.dumps(agent.snapshot()))
            restored = MNNLearningAgent.from_snapshot(snapshot, memory)
            self.assertEqual(restored.pending_action, "right")
            self.assertEqual(restored.pending_action_source, "memory")
            result = restored.resolve(1.0, context="busy evening")
            self.assertEqual(result["learning_update"]["action"], "right")
            self.assertIsNone(restored.pending_action)
            self.assertIsNone(restored.pending_action_source)

    def test_schema_v1_snapshot_remains_compatible(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["left", "right"]), memory)
            decision = agent.decide()
            snapshot = agent.snapshot()
            snapshot["schema_version"] = 1
            snapshot.pop("pending_action_source")
            restored = MNNLearningAgent.from_snapshot(snapshot, memory)
            self.assertEqual(restored.pending_action, decision["action"])
            self.assertEqual(restored.pending_action_source, "learner")

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
