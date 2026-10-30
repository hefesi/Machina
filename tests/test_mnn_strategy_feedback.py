import unittest

from machina.chemical_signaling import ChemicalEvent
from machina.mnn import Connection, MNN, Unit
from machina.mnn_organism import MNNOrganism
from machina.mnn_strategy_feedback import MNNStrategyFeedbackAdapter


class StrategyFeedbackAdapterTests(unittest.TestCase):
    def setUp(self):
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        network.add_unit(Unit("output", activation="identity"))
        network.add_connection(Connection("sensor-output", "sensor", "output", 0.5))
        self.organism = MNNOrganism("feedback-test", network=network, learning_rate=0.2)
        self.adapter = MNNStrategyFeedbackAdapter()
        self.proposal = {
            "status": "proposed",
            "action": "candidate",
            "context": "workload A",
            "evidence_ids": ["evidence-1", "evidence-2"],
        }
        self.organism.step({"sensor": 1.0}, ChemicalEvent(reward=0.2))

    def test_confirmed_outcome_reaches_chemical_and_neural_learning(self):
        before_weight = self.organism.network.connections["sensor-output"].weight
        result = self.adapter.apply(
            self.organism,
            self.proposal,
            execution_confirmed=True,
            executed_action="candidate",
            observed_reward=0.9,
            inputs={"sensor": 1.0},
            progress=0.8,
            uncertainty=0.2,
        )
        self.assertEqual("workload a", result.feedback.context)
        self.assertEqual(("evidence-1", "evidence-2"), result.feedback.evidence_ids)
        self.assertAlmostEqual(0.9, result.feedback.event.reward)
        self.assertEqual(2, result.organism_step.timestep)
        self.assertGreater(
            self.organism.network.connections["sensor-output"].weight, before_weight
        )

    def test_unconfirmed_execution_does_not_advance_organism(self):
        before = self.organism.snapshot()
        with self.assertRaises(ValueError):
            self.adapter.apply(
                self.organism, self.proposal,
                execution_confirmed=False, executed_action="candidate",
                observed_reward=0.9,
            )
        self.assertEqual(before, self.organism.snapshot())

    def test_mismatched_executed_action_is_rejected_without_learning(self):
        before = self.organism.snapshot()
        with self.assertRaises(ValueError):
            self.adapter.apply(
                self.organism, self.proposal,
                execution_confirmed=True, executed_action="baseline",
                observed_reward=0.9,
            )
        self.assertEqual(before, self.organism.snapshot())

    def test_abstention_cannot_be_used_as_executed_proposal(self):
        before = self.organism.snapshot()
        proposal = {**self.proposal, "status": "abstain", "action": None}
        with self.assertRaises(ValueError):
            self.adapter.apply(
                self.organism, proposal,
                execution_confirmed=True, executed_action="candidate",
                observed_reward=0.9,
            )
        self.assertEqual(before, self.organism.snapshot())

    def test_reward_must_be_normalized_before_entering_chemical_system(self):
        before = self.organism.snapshot()
        with self.assertRaises(ValueError):
            self.adapter.apply(
                self.organism, self.proposal,
                execution_confirmed=True, executed_action="candidate",
                observed_reward=2.0,
            )
        self.assertEqual(before, self.organism.snapshot())


if __name__ == "__main__":
    unittest.main()
