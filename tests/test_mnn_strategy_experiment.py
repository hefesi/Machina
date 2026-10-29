import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_strategy_experiment import MNNStrategyExperimentLog


class StrategyExperimentLogTests(unittest.TestCase):
    def test_proposal_and_outcome_are_append_only_and_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            with FragmentMemory(Path(tmp) / "memory.db") as memory:
                log = MNNStrategyExperimentLog(memory, ["baseline", "candidate"])
                review = {
                    "status": "candidate",
                    "reason": "recent reward margin",
                    "candidate_action": "candidate",
                    "evidence": {"candidate": {"recent_evidence_ids": ["reward-1"]}},
                }
                proposal = log.begin(
                    "trial-001", hypothesis="candidate improves recent reward",
                    context="workload A", current_action="baseline",
                    planned_action="candidate", review=review,
                )
                self.assertEqual("proposal", proposal.metadata["event"])
                self.assertEqual(["reward-1"], proposal.metadata["evidence_ids"])
                self.assertEqual(proposal.id, log.begin(
                    "trial-001", hypothesis="candidate improves recent reward",
                    context="workload A", current_action="baseline",
                    planned_action="candidate", review=review,
                ).id)
                outcome = log.complete(
                    "trial-001", tested_action="candidate", observed_reward=0.75,
                    decision="validate_candidate_further", observation="one trial",
                )
                self.assertFalse(outcome.metadata["policy_changed"])
                self.assertEqual(outcome.id, log.complete(
                    "trial-001", tested_action="candidate", observed_reward=0.75,
                    decision="validate_candidate_further", observation="one trial",
                ).id)
                self.assertEqual(2, len([
                    item for item in memory.archive()
                    if item.kind == "strategy-experiment"
                ]))

    def test_cannot_complete_unknown_or_different_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            with FragmentMemory(Path(tmp) / "memory.db") as memory:
                log = MNNStrategyExperimentLog(memory, ["baseline", "candidate"])
                with self.assertRaises(ValueError):
                    log.complete("missing", tested_action="baseline",
                        observed_reward=0.0, decision="keep_current")
                log.begin("trial-002", hypothesis="test", context="context",
                    current_action="baseline", planned_action="baseline",
                    review={"status": "maintain"})
                with self.assertRaises(ValueError):
                    log.complete("trial-002", tested_action="candidate",
                        observed_reward=0.0, decision="keep_current")

    def test_reusing_event_id_with_different_data_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with FragmentMemory(Path(tmp) / "memory.db") as memory:
                log = MNNStrategyExperimentLog(memory, ["baseline", "candidate"])
                kwargs = dict(experiment_id="trial-003", context="context",
                    current_action="baseline", planned_action="baseline",
                    review={"status": "maintain"})
                log.begin(hypothesis="first hypothesis", **kwargs)
                with self.assertRaises(ValueError):
                    log.begin(hypothesis="different hypothesis", **kwargs)


if __name__ == "__main__":
    unittest.main()
