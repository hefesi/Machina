import tempfile
import unittest
from pathlib import Path

from machina.contracts import Artifact, ContractKind, EpistemicStatus
from machina.event_store import EventStore
from machina.fragment_memory import FragmentMemory
from machina.mnn_autobiographical_recall import MNNAutobiographicalRecall
from machina.mnn_autobiographical_strategy_advisor import MNNAutobiographicalStrategyAdvisor
from machina.mnn_event_memory_projector import MNNEventMemoryProjector


class MNNAutobiographicalStrategyAdvisorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.store = EventStore(root / "events.db")
        self.memory = FragmentMemory(root / "memory.db")
        self.addCleanup(self.store.close)
        self.addCleanup(self.memory.close)
        for index, (action, reward) in enumerate([
            ("baseline", 0.30), ("baseline", 0.40), ("baseline", 0.35),
            ("candidate", 0.80), ("candidate", 0.85), ("candidate", 0.75),
        ]):
            cycle_id = f"cycle-{index}"
            self.store.create_cycle(cycle_id)
            data = {
                "proposal_id": f"proposal-{index}",
                "operation_id": f"operation-{index}",
                "action": action,
                "context": "motor maintenance",
                "expected_reward": 0.5,
                "observed_reward": reward,
                "prediction_error": reward - 0.5,
                "execution_confirmed": True,
                "evidence_ids": [],
            }
            artifact = Artifact.create(
                ContractKind.STRATEGY_OUTCOME,
                cycle_id=cycle_id,
                producer="test",
                data=data,
                epistemic_status=EpistemicStatus.OBSERVED,
            )
            self.store.append("strategy.outcome.recorded", artifact)
        self.projector = MNNEventMemoryProjector(self.store, self.memory)
        self.projector.project()
        self.advisor = MNNAutobiographicalStrategyAdvisor(
            MNNAutobiographicalRecall(self.memory),
            ["baseline", "candidate"],
            min_cycles_per_action=3,
            min_reward_margin=0.1,
        )

    def test_recommends_only_after_repeated_context_matched_outcomes(self):
        result = self.advisor.review("Motor   Maintenance", current_action="baseline")
        self.assertEqual("candidate", result["status"])
        self.assertEqual("candidate", result["candidate_action"])
        self.assertEqual(3, result["action_summaries"]["baseline"]["distinct_cycle_count"])
        self.assertEqual(3, result["action_summaries"]["candidate"]["distinct_cycle_count"])
        self.assertFalse(result["causal_claim"])
        self.assertFalse(result["policy_changed"])
        self.assertEqual(6, len(result["evidence_event_ids"]))

    def test_multiple_outcomes_in_one_cycle_do_not_overweight_that_cycle(self):
        artifact = Artifact.create(
            ContractKind.STRATEGY_OUTCOME,
            cycle_id="cycle-3",
            producer="test",
            data={
                "proposal_id": "proposal-extra",
                "operation_id": "operation-extra",
                "action": "candidate",
                "context": "motor maintenance",
                "expected_reward": 0.5,
                "observed_reward": 1.0,
                "prediction_error": 0.5,
                "execution_confirmed": True,
                "evidence_ids": [],
            },
            epistemic_status=EpistemicStatus.OBSERVED,
        )
        self.store.append("strategy.outcome.recorded", artifact)
        self.projector.project()
        result = self.advisor.review("motor maintenance", current_action="baseline")
        candidate = result["action_summaries"]["candidate"]
        self.assertEqual(3, candidate["sample_count"])
        self.assertEqual(4, candidate["outcome_count"])
        self.assertAlmostEqual((0.9 + 0.85 + 0.75) / 3, candidate["mean_observed_reward"])

    def test_context_mismatch_does_not_leak_other_context_outcomes(self):
        result = self.advisor.review("battery calibration", current_action="baseline")
        self.assertEqual("inconclusive", result["status"])
        self.assertIn("baseline", result["insufficient_actions"])

    def test_unknown_current_action_and_invalid_context_are_rejected(self):
        with self.assertRaises(ValueError):
            self.advisor.review(" ", current_action="baseline")
        with self.assertRaises(ValueError):
            self.advisor.review("motor maintenance", current_action="unknown")

    def test_requires_multiple_distinct_cycles_and_variability_samples(self):
        advisor = MNNAutobiographicalStrategyAdvisor(
            MNNAutobiographicalRecall(self.memory),
            ["baseline", "candidate"],
            min_cycles_per_action=4,
        )
        result = advisor.review("motor maintenance", current_action="baseline")
        self.assertEqual("inconclusive", result["status"])

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            MNNAutobiographicalStrategyAdvisor(
                MNNAutobiographicalRecall(self.memory),
                ["baseline", "candidate"],
                min_cycles_per_action=1,
            )


if __name__ == "__main__":
    unittest.main()
