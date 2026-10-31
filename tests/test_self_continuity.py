from __future__ import annotations

import json
import unittest

from machina.self_continuity import SelfContinuity


class SelfContinuityTests(unittest.TestCase):
    def test_commitment_revision_preserves_previous_values(self):
        identity = SelfContinuity("machina-01")
        first = identity.update_commitment(
            "protect_data", "Never delete user archives without review",
            reason="initial safety commitment", source="initialization",
        )
        second = identity.update_commitment(
            "protect_data", "Preserve archives and require verified recovery",
            reason="revised after recovery experiment", source="cycle-12",
        )
        self.assertIsNone(first["previous_value"])
        self.assertEqual(
            "Never delete user archives without review",
            second["previous_value"],
        )
        self.assertEqual("Preserve archives and require verified recovery",
                         identity.commitments["protect_data"])
        self.assertEqual(2, len(identity.commitment_history))
        self.assertEqual(2, len(identity.event_history))

    def test_retirement_removes_active_commitment_but_not_history(self):
        identity = SelfContinuity("machina-01")
        identity.update_commitment(
            "explore", "Investigate unknowns",
            reason="initial", source="bootstrap",
        )
        retired = identity.retire_commitment(
            "explore", reason="goal completed and no longer applicable",
            source="review-cycle-9",
        )
        self.assertIsNone(retired["new_value"])
        self.assertNotIn("explore", identity.commitments)
        self.assertEqual("Investigate unknowns",
                         identity.commitment_history[0]["new_value"])
        self.assertEqual(2, len(identity.commitment_history))

    def test_snapshot_round_trip_preserves_revision_history(self):
        identity = SelfContinuity("machina-01", component_versions={"mnn": "0.3"})
        identity.update_commitment(
            "continuity", "Preserve causal history",
            reason="identity baseline", source="bootstrap",
        )
        restored = SelfContinuity.from_snapshot(
            json.loads(json.dumps(identity.snapshot()))
        )
        self.assertEqual(identity.snapshot(), restored.snapshot())
        report = restored.continuity_report(identity)
        self.assertTrue(report["history_extends_previous"])
        self.assertTrue(report["commitment_history_extends_previous"])

    def test_snapshot_is_detached_and_corrupt_sequences_are_rejected(self):
        identity = SelfContinuity("machina-01")
        identity.update_commitment(
            "continuity", "Preserve history",
            reason="baseline", source="bootstrap",
        )
        snapshot = identity.snapshot()
        snapshot["commitments"]["continuity"] = "tampered"
        self.assertEqual("Preserve history", identity.commitments["continuity"])
        invalid = identity.snapshot()
        invalid["commitment_history"][0]["sequence"] = 7
        with self.assertRaisesRegex(ValueError, "sequence"):
            SelfContinuity.from_snapshot(invalid)

    def test_unchanged_or_unknown_commitments_cannot_be_revised_or_retired(self):
        identity = SelfContinuity("machina-01")
        identity.update_commitment(
            "continuity", "Preserve history",
            reason="baseline", source="bootstrap",
        )
        with self.assertRaisesRegex(ValueError, "unchanged"):
            identity.update_commitment(
                "continuity", "Preserve history",
                reason="duplicate", source="review",
            )
        with self.assertRaises(ValueError):
            identity.retire_commitment(
                "missing", reason="not active", source="review",
            )
        self.assertEqual(1, len(identity.commitment_history))


if __name__ == "__main__":
    unittest.main()
