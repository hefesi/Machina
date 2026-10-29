import json
import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn import Connection, MNN, Unit
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent
from machina.mnn_experience import MNNExperienceCycle
from machina.mnn_integrated_loop import MNNIntegratedExperienceLoop


class MNNIntegratedExperienceLoopTests(unittest.TestCase):
    def make_loop(self, memory):
        network = MNN(weight_limit=2.0)
        network.add_unit(Unit("cue_left", activation="identity"))
        network.add_unit(Unit("cue_right", activation="identity"))
        network.add_unit(Unit("outcome", bias=1.0, activation="identity"))
        network.add_connection(Connection("left-outcome", "cue_left", "outcome", 0.2))
        network.add_connection(Connection("right-outcome", "cue_right", "outcome", 0.2))
        agent = MNNLearningAgent(
            MNNActionLearner(["left", "right"], learning_rate=0.5), memory
        )
        cycle = MNNExperienceCycle(network, learning_rate=0.1)
        return MNNIntegratedExperienceLoop(
            agent, cycle, action_inputs={"left": "cue_left", "right": "cue_right"}
        )

    def test_decision_reward_updates_action_values_neural_weights_and_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            with FragmentMemory(path) as memory:
                loop = self.make_loop(memory)
                initial_left = loop.experience_cycle.network.connections["left-outcome"].weight
                decision = loop.decide(context="controlled test")
                self.assertEqual(decision["action"], "left")
                self.assertEqual(decision["neural_step"], 1)
                result = loop.resolve(1.0, context="controlled test")
                self.assertGreater(result["action_learning"]["prediction_after"], 0.0)
                self.assertGreater(
                    loop.experience_cycle.network.connections["left-outcome"].weight,
                    initial_left,
                )
                self.assertEqual(memory.count(), 1)
                self.assertEqual(result["experience_count"], 1)
                self.assertEqual(loop.experience_cycle.pending_steps, 0)

            with FragmentMemory(path) as reopened:
                self.assertEqual(reopened.count(), 1)
                self.assertTrue(reopened.recall("controlled test"))

    def test_checkpoint_restores_pending_decision_and_neural_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            with FragmentMemory(path) as memory:
                loop = self.make_loop(memory)
                loop.decide(context="pending episode")
                checkpoint = json.loads(json.dumps(loop.snapshot()))
                restored = MNNIntegratedExperienceLoop.from_snapshot(
                    checkpoint, memory=memory
                )
                self.assertEqual(restored.agent.pending_action, "left")
                self.assertEqual(restored.experience_cycle.pending_steps, 1)
                result = restored.resolve(1.0, context="pending episode")
                self.assertGreater(result["neural_plasticity"]["left-outcome"], 0.0)
                self.assertEqual(memory.count(), 1)

    def test_cannot_start_second_decision_before_resolving_reward(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(
            Path(directory) / "memory.sqlite3"
        ) as memory:
            loop = self.make_loop(memory)
            loop.decide()
            with self.assertRaises(RuntimeError):
                loop.decide()
            with self.assertRaises(ValueError):
                loop.resolve(float("nan"))
            # Invalid reward does not consume the pending experience.
            self.assertEqual(loop.experience_cycle.pending_steps, 1)
            loop.resolve(0.0)

    def test_rejects_missing_or_duplicate_action_input_units(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(
            Path(directory) / "memory.sqlite3"
        ) as memory:
            loop = self.make_loop(memory)
            with self.assertRaises(ValueError):
                MNNIntegratedExperienceLoop(
                    loop.agent, loop.experience_cycle, action_inputs={"left": "cue_left"}
                )
            with self.assertRaises(ValueError):
                MNNIntegratedExperienceLoop(
                    loop.agent, loop.experience_cycle,
                    action_inputs={"left": "cue_left", "right": "cue_left"},
                )


if __name__ == "__main__":
    unittest.main()
