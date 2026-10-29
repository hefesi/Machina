import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent
from machina.mnn_strategy_experiment import MNNStrategyExperimentLog


class AgentExperimentLogTests(unittest.TestCase):
    def test_agent_records_proposal_and_outcome_without_switching_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            with FragmentMemory(Path(tmp) / "memory.db") as memory:
                learner = MNNActionLearner(["baseline", "candidate"])
                log = MNNStrategyExperimentLog(memory, learner.actions)
                agent = MNNLearningAgent(learner, memory, strategy_experiment_log=log)
                decision = {
                    "action": "baseline",
                    "context": "workload A",
                    "strategy_review": {
                        "status": "candidate",
                        "candidate_action": "candidate",
                        "reason": "recent reward margin",
                        "evidence": {"candidate": {"recent_evidence_ids": ["evidence-1"]}},
                    },
                }
                before = learner.snapshot()
                proposal = agent.record_strategy_experiment_proposal(
                    "agent-trial-1", decision,
                    hypothesis="candidate performs better on workload A",
                )
                self.assertEqual("candidate", proposal.metadata["planned_action"])
                self.assertEqual(["evidence-1"], proposal.metadata["evidence_ids"])
                self.assertEqual(before, learner.snapshot())
                outcome = agent.record_strategy_experiment_outcome(
                    "agent-trial-1", tested_action="candidate", observed_reward=0.8,
                    decision="validate_candidate_further",
                )
                self.assertFalse(outcome.metadata["policy_changed"])
                self.assertEqual(before, learner.snapshot())
                self.assertIsNone(agent.pending_action)

    def test_integration_requires_log_and_contextual_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            with FragmentMemory(Path(tmp) / "memory.db") as memory:
                learner = MNNActionLearner(["baseline", "candidate"])
                agent = MNNLearningAgent(learner, memory)
                with self.assertRaises(ValueError):
                    agent.record_strategy_experiment_proposal(
                        "trial", {"action": "baseline", "context": "ctx",
                        "strategy_review": {"status": "maintain"}},
                        hypothesis="test",
                    )
                log = MNNStrategyExperimentLog(memory, learner.actions)
                agent = MNNLearningAgent(learner, memory, strategy_experiment_log=log)
                with self.assertRaises(ValueError):
                    agent.record_strategy_experiment_proposal(
                        "trial", {"action": "baseline", "context": "",
                        "strategy_review": {"status": "maintain"}},
                        hypothesis="test",
                    )


if __name__ == "__main__":
    unittest.main()
