import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn import Connection, MNN, Unit
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent
from machina.mnn_contextual_outcome_policy import MNNContextualOutcomePolicy
from machina.mnn_experience import MNNExperienceCycle
from machina.mnn_integrated_loop import MNNIntegratedExperienceLoop


class MNNContextualPolicyIntegrationTests(unittest.TestCase):
    def add_evidence(self, memory, context, preferred, prefix):
        for action in ("left", "right"):
            reward = 1.0 if action == preferred else 0.0
            for index in range(3):
                memory.add(
                    f"Observed {action} in {context} with reward {reward:g}",
                    kind="action-outcome",
                    source_uri=f"test://{prefix}/{action}/{index}",
                    confidence=1.0,
                    tags=("action-learning", action),
                    metadata={
                        "action": action,
                        "reward": reward,
                        "context": context,
                        "decision": len(memory.archive()) + 1,
                    },
                )

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
        learner = MNNActionLearner(["left", "right"], learning_rate=0.5)
        policy = MNNContextualOutcomePolicy(
            memory,
            ["left", "right"],
            min_samples_per_action=2,
            min_reward_margin=0.1,
            min_context_overlap=0.6,
        )
        agent = MNNLearningAgent(learner, memory, outcome_policy=policy)
        cycle = MNNExperienceCycle(network, learning_rate=0.1)
        return MNNIntegratedExperienceLoop(
            agent,
            cycle,
            action_inputs={"left": "cue_left", "right": "cue_right"},
            context_inputs={"quiet": "ctx_quiet", "busy": "ctx_busy"},
        )

    def test_context_changes_action_selection_in_integrated_loop(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(
            Path(directory) / "memory.sqlite3"
        ) as memory:
            self.add_evidence(memory, "quiet workload", "left", "quiet")
            self.add_evidence(memory, "busy workload", "right", "busy")
            loop = self.make_loop(memory)

            quiet = loop.decide(context="quiet workload", use_outcome_policy=True)
            self.assertEqual(quiet["action"], "left")
            self.assertEqual(quiet["selection_source"], "outcome_policy")
            self.assertEqual(quiet["context_cues"], ["quiet"])
            loop.resolve(1.0, context="quiet workload")

            busy = loop.decide(context="busy workload", use_outcome_policy=True)
            self.assertEqual(busy["action"], "right")
            self.assertEqual(busy["selection_source"], "outcome_policy")
            self.assertEqual(busy["context_cues"], ["busy"])
            loop.resolve(1.0, context="busy workload")

    def test_policy_abstention_falls_back_to_action_learner(self):
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(
            Path(directory) / "memory.sqlite3"
        ) as memory:
            loop = self.make_loop(memory)
            decision = loop.decide(context="unseen workload", use_outcome_policy=True)
            self.assertEqual(decision["selection_source"], "learner")
            self.assertTrue(decision["request_experience"])
            loop.resolve(0.0, context="unseen workload")


if __name__ == "__main__":
    unittest.main()
