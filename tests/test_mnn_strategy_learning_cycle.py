import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn import Connection, MNN, Unit
from machina.mnn_organism import MNNOrganism
from machina.mnn_knowledge_use_feedback import MNNKnowledgeUseFeedback
from machina.mnn_strategy_decision_advisor import MNNStrategyDecisionAdvisor
from machina.mnn_strategy_context_memory import MNNStrategyContextMemory
from machina.mnn_strategy_evaluation import MNNStrategyExperimentEvaluator
from machina.mnn_strategy_feedback import MNNStrategyFeedbackAdapter
from machina.mnn_strategy_learning_cycle import MNNStrategyLearningCycle


class StrategyLearningCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.memory = FragmentMemory(Path(self.tmp.name) / "memory.db")
        self.addCleanup(self.memory.close)
        self.evidence = self.memory.add(
            "Evidence for workload A", kind="note", tags=("workload-a",)
        )
        self.proposal = {
            "status": "proposed", "action": "candidate",
            "context": "workload A", "evidence_ids": [self.evidence.id],
        }
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        network.add_unit(Unit("output", activation="identity"))
        network.add_connection(Connection("sensor-output", "sensor", "output", 0.5))
        self.organism = MNNOrganism(
            "cycle-test", network=network, learning_rate=0.2
        )
        evaluator = MNNStrategyExperimentEvaluator(self.memory, ["baseline", "candidate"])
        self.advisor = MNNStrategyDecisionAdvisor(MNNStrategyContextMemory(evaluator))
        self.cycle = MNNStrategyLearningCycle(
            self.advisor,
            MNNStrategyFeedbackAdapter(),
            MNNKnowledgeUseFeedback(self.memory),
        )

    def test_proposal_delegates_without_executing(self):
        result = self.cycle.propose("workload A", ["campaign-1"])
        self.assertEqual("abstain", result["status"])
        self.assertIsNone(result["action"])
        self.assertEqual(0, self.organism.network.timestep)

    def test_strategy_outcome_requires_confirmation_and_updates_organism(self):
        with self.assertRaises(ValueError):
            self.cycle.learn_strategy_outcome(
                self.organism, self.proposal, execution_confirmed=False,
                executed_action="candidate", observed_reward=0.9,
            )
        result = self.cycle.learn_strategy_outcome(
            self.organism, self.proposal, execution_confirmed=True,
            executed_action="candidate", observed_reward=0.9,
            inputs={"sensor": 1.0}, progress=0.8,
        )
        self.assertEqual(1, result.organism_step.timestep)

    def test_evidence_feedback_is_separate_and_idempotent(self):
        result = self.cycle.learn_evidence_use(
            self.proposal, {self.evidence.id: True},
            execution_confirmed=True, executed_action="candidate",
            operation_id="outcome-1",
        )
        repeated = self.cycle.learn_evidence_use(
            self.proposal, {self.evidence.id: True},
            execution_confirmed=True, executed_action="candidate",
            operation_id="outcome-1",
        )
        self.assertTrue(result.applied)
        self.assertFalse(repeated.applied)
        self.assertEqual(0.6, self.memory.context_importance(
            self.evidence.id, "workload A"
        ))

    def test_evidence_feedback_rejects_unconfirmed_execution(self):
        with self.assertRaises(ValueError):
            self.cycle.learn_evidence_use(
                self.proposal, {self.evidence.id: True},
                execution_confirmed=False, executed_action="candidate",
                operation_id="outcome-2",
            )
        self.assertEqual(0.5, self.memory.context_importance(
            self.evidence.id, "workload A"
        ))


if __name__ == "__main__":
    unittest.main()
