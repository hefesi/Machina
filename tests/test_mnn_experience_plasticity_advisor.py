import tempfile
import unittest
from pathlib import Path

from machina.contracts import Artifact, ContractKind, EpistemicStatus
from machina.event_store import EventStore
from machina.fragment_memory import FragmentMemory
from machina.mnn import Connection, MNN, Unit
from machina.mnn_autobiographical_recall import MNNAutobiographicalRecall
from machina.mnn_autobiographical_strategy_advisor import MNNAutobiographicalStrategyAdvisor
from machina.mnn_event_memory_projector import MNNEventMemoryProjector
from machina.mnn_experience_plasticity_advisor import MNNExperiencePlasticityAdvisor
from machina.mnn_plasticity_control import MNNPlasticityController


class MNNExperiencePlasticityAdvisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = EventStore(root / "events.db")
        self.memory = FragmentMemory(root / "memory.db")
        self.addCleanup(self.store.close)
        self.addCleanup(self.memory.close)
        records = [
            ("baseline", 0.30), ("baseline", 0.40), ("baseline", 0.35),
            ("candidate", 0.80), ("candidate", 0.85), ("candidate", 0.75),
        ]
        for index, (action, reward) in enumerate(records):
            cycle_id = f"cycle-{index}"
            self.store.create_cycle(cycle_id)
            artifact = Artifact.create(
                ContractKind.STRATEGY_OUTCOME,
                cycle_id=cycle_id,
                producer="test",
                data={
                    "proposal_id": f"proposal-{index}",
                    "operation_id": f"operation-{index}",
                    "action": action,
                    "context": "motor maintenance",
                    "expected_reward": 0.5,
                    "observed_reward": reward,
                    "prediction_error": reward - 0.5,
                    "execution_confirmed": True,
                    "evidence_ids": [],
                },
                epistemic_status=EpistemicStatus.OBSERVED,
            )
            self.store.append("strategy.outcome.recorded", artifact)
        MNNEventMemoryProjector(self.store, self.memory).project()
        self.strategy = MNNAutobiographicalStrategyAdvisor(
            MNNAutobiographicalRecall(self.memory),
            ["baseline", "candidate"],
            min_cycles_per_action=3,
            min_reward_margin=0.1,
        )
        self.network = MNN(weight_limit=2.0)
        self.network.add_unit(Unit("pre", state=0.8, activation="identity"))
        self.network.add_unit(Unit("post", state=0.5, activation="identity"))
        self.network.add_connection(Connection("candidate-edge", "pre", "post", 0.4))
        self.network.add_connection(Connection("unmapped-edge", "post", "pre", 0.2))
        self.controller = MNNPlasticityController()
        self.adapter = MNNExperiencePlasticityAdvisor(
            self.strategy,
            self.controller,
            self.network,
            {"candidate": ["candidate-edge"]},
        )

    def test_review_creates_evidence_linked_proposal_without_mutation(self):
        before = self.network.snapshot()
        proposal = self.adapter.review_and_propose(
            "Motor Maintenance",
            current_action="baseline",
            proposal_id="experience-p1",
            learning_rate=0.1,
            max_delta=0.01,
        )
        self.assertIsNotNone(proposal)
        self.assertEqual(before, self.network.snapshot())
        self.assertEqual("candidate", proposal.action)
        self.assertEqual(3, len(proposal.cycle_ids))
        self.assertEqual(3, len(proposal.evidence_event_ids))
        self.assertEqual(("candidate-edge",), proposal.connection_ids)
        self.assertEqual({"candidate-edge"}, set(proposal.plasticity.proposed_weights))

    def test_apply_is_explicit_and_rollback_is_conditional(self):
        proposal = self.adapter.review_and_propose(
            "motor maintenance", current_action="baseline",
            proposal_id="experience-p2", learning_rate=0.1,
        )
        before = self.network.connections["candidate-edge"].weight
        self.adapter.apply(proposal)
        self.assertGreater(self.network.connections["candidate-edge"].weight, before)
        self.adapter.rollback(proposal)
        self.assertEqual(before, self.network.connections["candidate-edge"].weight)

    def test_later_weight_change_blocks_rollback(self):
        proposal = self.adapter.review_and_propose(
            "motor maintenance", current_action="baseline",
            proposal_id="experience-p3", learning_rate=0.1,
        )
        self.adapter.apply(proposal)
        self.network.connections["candidate-edge"].weight += 0.01
        with self.assertRaises(ValueError):
            self.adapter.rollback(proposal)

    def test_inconclusive_history_produces_no_plasticity_proposal(self):
        proposal = self.adapter.review_and_propose(
            "unseen context", current_action="baseline",
            proposal_id="experience-p4", learning_rate=0.1,
        )
        self.assertIsNone(proposal)

    def test_connection_mapping_must_be_explicit_and_valid(self):
        with self.assertRaises(ValueError):
            MNNExperiencePlasticityAdvisor(
                self.strategy, self.controller, self.network,
                {"candidate": ["not-a-real-edge"]},
            )


if __name__ == "__main__":
    unittest.main()
