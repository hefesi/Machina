from __future__ import annotations

import tempfile
import unittest

from machina import NormalizedPerception, VirtualBrain


class NormalizedPerceptionTests(unittest.TestCase):
    def test_contract_preserves_raw_and_normalized_payload_in_brain_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = {"transcript": "turn left"}
            perception = NormalizedPerception(
                content={"intent": "navigation", "direction": "left"},
                raw_payload=raw,
                modality="audio_transcript",
                source={"type": "microphone", "name": "front_mic", "reliability": 0.92},
                confidence=0.84,
                raw_reference="capture:session-1",
                transformations=("speech_to_text", "intent_normalization"),
            )
            brain = VirtualBrain(f"{directory}/brain.sqlite3")
            try:
                cycle_id = brain.start_cycle(perception, "Navigate safely")
                artifact = brain._required(cycle_id, "observation.received")
                self.assertEqual("audio_transcript", artifact.data["modality"])
                self.assertEqual({"intent": "navigation", "direction": "left"}, artifact.data["content"])
                self.assertEqual(raw, artifact.data["raw_payload"])
                self.assertEqual("capture:session-1", artifact.data["raw_reference"])
                self.assertEqual(["speech_to_text", "intent_normalization"], artifact.data["transformations"])
                self.assertEqual(0.84, artifact.confidence)
                self.assertEqual(0.92, artifact.data["reliability"])
            finally:
                brain.close()

    def test_workspace_builds_unified_internal_state_after_cognition(self):
        with tempfile.TemporaryDirectory() as directory:
            brain = VirtualBrain(f"{directory}/brain.sqlite3")
            try:
                perception = NormalizedPerception(
                    content={"intent": "inspect"},
                    raw_payload={"text": "inspect the room"},
                    modality="text",
                    source={"type": "sensor", "name": "test-sensor", "reliability": 0.9},
                    confidence=0.88,
                )
                cycle_id = brain.start_cycle(perception, "Inspect safely")
                brain.advance(cycle_id, stop_after="decision.requested")
                workspace = brain._required(cycle_id, "workspace.cognition_updated")
                state = workspace.data["internal_state"]
                self.assertEqual("machina.internal_state.v1", state["schema_version"])
                self.assertEqual(cycle_id, state["cycle_id"])
                self.assertEqual("text", state["modality"])
                self.assertEqual(0.88, state["perception_confidence"])
                self.assertEqual(workspace.data["cognitive_result_ref"], state["cognitive_result_ref"])
                self.assertEqual(workspace.data["retrieved_memory_ids"], state["retrieved_memory_refs"])
                self.assertEqual('{"intent": "inspect"}', state["understanding"]["summary"])
            finally:
                brain.close()

    def test_contract_rejects_invalid_confidence_and_non_json_payload(self):
        with self.assertRaises(ValueError):
            NormalizedPerception(content="x", modality="text", source={}, confidence=1.2)
        with self.assertRaises(ValueError):
            NormalizedPerception(content=object(), modality="text", source={})

    def test_legacy_observation_path_remains_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            brain = VirtualBrain(f"{directory}/brain.sqlite3")
            try:
                cycle_id = brain.start_cycle("hello", "Respond")
                artifact = brain._required(cycle_id, "observation.received")
                self.assertEqual("hello", artifact.data["content"])
                self.assertEqual("event", artifact.data["modality"])
                self.assertEqual(1.0, artifact.confidence)
            finally:
                brain.close()


if __name__ == "__main__":
    unittest.main()
