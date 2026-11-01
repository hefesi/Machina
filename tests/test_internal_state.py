from __future__ import annotations

import unittest

from machina import InternalStateSnapshot


class InternalStateSnapshotTests(unittest.TestCase):
    def test_round_trip_preserves_shared_cycle_representation(self):
        snapshot = InternalStateSnapshot(
            cycle_id="cycle-1",
            observation_ref="observation-1",
            modality="image",
            source_ref="camera-1",
            perception_confidence=0.83,
            active_goal_ref="goal-1",
            retrieved_memory_refs=("memory-1", "memory-2"),
            cognitive_result_ref="cognition-1",
            understanding={"objects": ["door"]},
            uncertainties=({"topic": "distance", "confidence": 0.4},),
            mnn_signal={"activation": 0.62},
        )
        restored = InternalStateSnapshot.from_dict(snapshot.to_dict())
        self.assertEqual(snapshot, restored)

    def test_rejects_unknown_schema_version(self):
        with self.assertRaises(ValueError):
            InternalStateSnapshot.from_dict({"schema_version": "future"})

    def test_rejects_invalid_confidence(self):
        with self.assertRaises(ValueError):
            InternalStateSnapshot(
                cycle_id="c", observation_ref="o", modality="text",
                source_ref="s", perception_confidence=1.5, active_goal_ref="g"
            )


if __name__ == "__main__":
    unittest.main()
