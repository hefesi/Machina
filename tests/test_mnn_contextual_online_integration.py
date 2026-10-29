import json
import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn import Connection, MNN, Unit
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent
from machina.mnn_contextual_action_learning import MNNContextualActionLearner
from machina.mnn_experience import MNNExperienceCycle
from machina.mnn_integrated_loop import MNNIntegratedExperienceLoop


class MNNContextualOnlineIntegrationTests(unittest.TestCase):
    def make_loop(self, memory):
        network = MNN(weight_limit=2.0)
        for name in ("cue_left", "cue_right", "ctx_quiet", "ctx_busy"):
            network.add_unit(Unit(name, activation="identity"))
        network.add_unit(Unit("outcome", bias=1.0, activation="identity"))
        for edge, source in (
            ("left-outcome", "cue_left"),
            ("right-outcome", "cue_right"),
            ("quiet-outcome", "ctx_quiet"),
            ("busy-outcome", "ctx_busy"),
        ):
            network.add_connection(Connection(edge, source, "outcome", 0.2))
        agent = MNNLearningAgent(
            MNNActionLearner(["left", "right"], learning_rate=0.5), memory
        )
        cycle = MNNExperienceCycle(network, learning_rate=0.1)
        contextual = MNNContextualActionLearner(
            ["left", "right"], min_samples_per_action=2, min_reward_margin=0.1
        )
        return MNNIntegratedExperienceLoop(
            agent, cycle,
            action_inputs={"left": "cue_left", "right": "cue_right"},
            context_inputs={"quiet": "ctx_quiet", "busy": "ctx_busy"},
            contextual_learner=contextual,
        )

    def train_context(self, loop, context, preferred):
        for _ in range(3):
            for action in ("left", "right"):
                # Prime the contextual learner from previously observed trials.
                loop.contextual_learner.observe(
                    context, action, 1.0 if action == preferred else 0.0
                )

    def test_contextual_values_override_global_fallback_and_update_online(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(
            Path(directory) / "memory.sqlite3"
        ) as memory:
            loop = self.make_loop(memory)
            self.train_context(loop, "quiet workload", "left")
            self.train_context(loop, "busy workload", "right")

            quiet = loop.decide(context="quiet workload")
            self.assertEqual(quiet["action"], "left")
            self.assertEqual(quiet["selection_source"], "contextual_learner")
            self.assertEqual(quiet["contextual_learning"]["status"], "recommended")
            update = loop.resolve(1.0, context="quiet workload")
            self.assertIsNotNone(update["contextual_learning_update"])
            self.assertEqual(update["contextual_learning_update"]["action"], "left")

            busy = loop.decide(context="busy workload")
            self.assertEqual(busy["action"], "right")
            self.assertEqual(busy["selection_source"], "contextual_learner")
            loop.resolve(1.0, context="busy workload")

    def test_unknown_context_falls_back_and_is_learned_after_outcome(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(
            Path(directory) / "memory.sqlite3"
        ) as memory:
            loop = self.make_loop(memory)
            decision = loop.decide(context="unknown situation")
            self.assertEqual(decision["selection_source"], "learner")
            self.assertEqual(decision["contextual_learning"]["status"], "abstain")
            action = decision["action"]
            loop.resolve(0.8, context="unknown situation")
            self.assertEqual(
                loop.contextual_learner.snapshot()["counts"]["situation unknown"][action], 1
            )

    def test_snapshot_round_trip_preserves_pending_contextual_choice(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(
            Path(directory) / "memory.sqlite3"
        ) as memory:
            loop = self.make_loop(memory)
            self.train_context(loop, "quiet workload", "left")
            self.train_context(loop, "busy workload", "right")
            decision = loop.decide(context="busy workload")
            self.assertEqual(decision["action"], "right")
            checkpoint = json.loads(json.dumps(loop.snapshot(), allow_nan=False))
            restored = MNNIntegratedExperienceLoop.from_snapshot(checkpoint, memory=memory)
            self.assertEqual(restored.agent.pending_action, "right")
            self.assertEqual(restored.agent.pending_action_source, "contextual_learner")
            self.assertEqual(
                restored.contextual_learner.recommend("busy workload")["action"], "right"
            )
            restored.resolve(1.0, context="busy workload")
            self.assertEqual(memory.count(), 1)


if __name__ == "__main__":
    unittest.main()
