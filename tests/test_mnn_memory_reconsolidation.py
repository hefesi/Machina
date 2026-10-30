"""Tests for explicit, compare-and-swap memory reconsolidation proposals."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import FragmentMemory, MNNMemoryReconsolidationPipeline


class MNNMemoryReconsolidationPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.memory = FragmentMemory(Path(self.temp.name) / "memory.sqlite3")
        self.memory.add(
            "Initial understanding", source_uri="test://source",
            fragment_id="memory-1", confidence=0.5,
        )
        self.pipeline = MNNMemoryReconsolidationPipeline()

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def test_proposal_is_side_effect_free_and_apply_records_evidence(self):
        proposal = self.pipeline.propose(
            self.memory, "memory-1", revised_content="Evidence-adjusted understanding",
            evidence_id="source:observation-2", confidence=0.8,
        )
        self.assertEqual("Initial understanding", self.memory.get(
            "memory-1", record_access=False
        ).content)
        current, revision, applied = self.pipeline.apply(
            self.memory, proposal, operation_id="revision-2"
        )
        self.assertTrue(applied)
        self.assertEqual("Evidence-adjusted understanding", current.content)
        self.assertEqual("source:observation-2", revision["evidence_id"])
        self.assertEqual("Initial understanding", revision["prior_content"])

    def test_stale_proposal_cannot_overwrite_newer_revision(self):
        stale = self.pipeline.propose(
            self.memory, "memory-1", revised_content="Stale rewrite",
            evidence_id="evidence:stale",
        )
        self.memory.reconsolidate(
            "memory-1", revised_content="Newer accepted content",
            evidence_id="evidence:new", operation_id="newer-operation",
        )
        with self.assertRaisesRegex(ValueError, "stale memory revision proposal"):
            self.pipeline.apply(self.memory, stale, operation_id="stale-operation")
        self.assertEqual(
            "Newer accepted content",
            self.memory.get("memory-1", record_access=False).content,
        )
        self.assertEqual(1, len(self.memory.revision_history("memory-1")))

    def test_retry_of_same_proposal_is_idempotent(self):
        proposal = self.pipeline.propose(
            self.memory, "memory-1", revised_content="Revised",
            evidence_id="evidence:1",
        )
        first = self.pipeline.apply(self.memory, proposal, operation_id="same-op")
        second = self.pipeline.apply(self.memory, proposal, operation_id="same-op")
        self.assertTrue(first[2])
        self.assertFalse(second[2])
        self.assertEqual(1, len(self.memory.revision_history("memory-1")))

    def test_reusing_operation_id_with_another_proposal_is_rejected(self):
        first = self.pipeline.propose(
            self.memory, "memory-1", revised_content="First",
            evidence_id="evidence:1",
        )
        self.pipeline.apply(self.memory, first, operation_id="shared-op")
        second = self.pipeline.propose(
            self.memory, "memory-1", revised_content="Second",
            evidence_id="evidence:2",
        )
        with self.assertRaises(ValueError):
            self.pipeline.apply(self.memory, second, operation_id="shared-op")


    def test_autobiographical_context_must_contain_the_declared_evidence(self):
        from types import SimpleNamespace

        match = SimpleNamespace(
            evidence_refs=("evidence:cycle-4",),
            experience_records=({"event_id": "experience:event-8"},),
        )
        proposal = self.pipeline.propose_from_autobiographical_context(
            self.memory, "memory-1",
            revised_content="Updated using a prior experience",
            evidence_id="experience:event-8",
            autobiographical_matches=(match,),
        )
        self.assertEqual(
            ("evidence:cycle-4", "experience:event-8"),
            proposal.context_refs,
        )
        self.assertEqual(
            "Initial understanding",
            self.memory.get("memory-1", record_access=False).content,
        )

    def test_autobiographical_recall_is_not_accepted_as_unlinked_evidence(self):
        from types import SimpleNamespace

        match = SimpleNamespace(evidence_refs=("evidence:real",), experience_records=())
        with self.assertRaisesRegex(ValueError, "must match an explicit evidence"):
            self.pipeline.propose_from_autobiographical_context(
                self.memory, "memory-1",
                revised_content="Unsupported update",
                evidence_id="evidence:invented",
                autobiographical_matches=(match,),
            )

    def test_empty_autobiographical_context_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            self.pipeline.propose_from_autobiographical_context(
                self.memory, "memory-1",
                revised_content="Unsupported update",
                evidence_id="evidence:1",
                autobiographical_matches=(),
            )


if __name__ == "__main__":
    unittest.main()
