from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import (
    Artifact, ContractKind, FragmentMemory, MNN, MNNOrganism,
    MNNOrganismAgencyAdapter, Unit,
)


class MNNOrganismAgencyAdapterTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.directory.name) / "memory.sqlite")
        network = MNN()
        network.add_unit(Unit("memory_context", activation="identity"))
        self.organism = MNNOrganism("agency-bridge-test", network=network, memory=self.memory)
        self.goal = Artifact.create(
            ContractKind.GOAL, cycle_id="agency-test", producer="test",
            data={"description": "Choose a safe way to preserve project data",
                  "priority": 1, "constraints": [], "success_criteria": []},
        )
        self.workspace = Artifact.create(
            ContractKind.WORKSPACE_STATE, cycle_id="agency-test", producer="test",
            data={"context": "project data preservation", "active_percept_ids": [],
                  "retrieved_memory_ids": [], "active_goal_ref": self.goal.id,
                  "self_state": {}, "world_state": {}, "uncertainties": []},
            input_refs=[self.goal.id],
        )
        self.request = Artifact.create(
            ContractKind.DECISION_REQUEST, cycle_id="agency-test", producer="test",
            data={"workspace_ref": self.workspace.id, "active_goal_ref": self.goal.id,
                  "cognitive_result_refs": [], "constraints": [], "values": [],
                  "risks": [], "permissions": []},
            input_refs=[self.workspace.id, self.goal.id],
        )
        self.cognitive = Artifact.create(
            ContractKind.COGNITIVE_RESULT, cycle_id="agency-test", producer="test",
            data={
                "request_ref": self.request.id, "understanding": {}, "hypotheses": [],
                "inferences": [], "candidate_solutions": [],
                "candidate_plans": [
                    {"plan_id": "delete", "action": "delete", "target": "project archive",
                     "expected_outcome": "remove project archive permanently", "base_utility": 0.35},
                    {"plan_id": "preserve", "action": "preserve", "target": "project archive",
                     "expected_outcome": "preserve project data safely", "base_utility": 0.10},
                ],
                "predictions": [], "simulations": [], "uncertainty": [],
                "assumptions": [], "provenance": [],
            },
            input_refs=[self.request.id],
        )

    def tearDown(self):
        self.memory.close()
        self.directory.cleanup()

    def decide(self, organism=None):
        adapter = MNNOrganismAgencyAdapter(
            organism or self.organism, target_unit="memory_context", memory_weight=0.5
        )
        return adapter.decide(
            goal=self.goal, workspace=self.workspace,
            cognitive_result=self.cognitive, request=self.request,
        )

    def test_relevant_past_experience_can_change_selected_candidate(self):
        self.memory.add(
            "Preserve project archive data safely. The preserve action succeeded and prevented permanent data loss.",
            kind="episode", source_uri="test://project-preservation",
            importance=1.0, confidence=1.0,
            tags=("preserve", "archive", "data"),
            fragment_id="successful-preservation",
        )
        decision = self.decide()
        self.assertEqual("preserve", decision["selected_plan"]["action"])
        guidance = decision["rationale"]["memory_guidance"]
        self.assertEqual("applied", guidance["status"])
        self.assertIn("successful-preservation", guidance["selected_evidence_ids"])
        self.assertGreater(
            guidance["candidate_scores"]["000001:preserve"],
            guidance["candidate_scores"]["000000:delete"],
        )

    def test_no_relevant_memory_preserves_base_policy_selection(self):
        self.memory.add(
            "The weather was sunny during an unrelated walk.",
            kind="episode", source_uri="test://unrelated",
            importance=1.0, confidence=1.0, fragment_id="unrelated-memory",
        )
        decision = self.decide()
        self.assertEqual("delete", decision["selected_plan"]["action"])
        self.assertEqual("no_relevant_evidence", decision["rationale"]["memory_guidance"]["status"])

    def test_no_memory_archive_falls_back_without_changing_policy(self):
        organism = MNNOrganism("no-memory", network=self.organism.network)
        decision = self.decide(organism)
        self.assertEqual("delete", decision["selected_plan"]["action"])
        self.assertEqual("not_applied", decision["rationale"]["memory_guidance"]["status"])

    def test_memory_weight_is_bounded(self):
        with self.assertRaises(ValueError):
            MNNOrganismAgencyAdapter(self.organism, target_unit="memory_context", memory_weight=1.1)


if __name__ == "__main__":
    unittest.main()
