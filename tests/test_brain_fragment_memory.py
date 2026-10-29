from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from machina import VirtualBrain


class VirtualBrainFragmentMemoryTests(unittest.TestCase):
    def test_episode_fragments_persist_and_are_recalled_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brain_path = root / "brain.sqlite"
            fragments_path = root / "fragments.sqlite"

            first_brain = VirtualBrain(
                brain_path,
                fragment_memory_path=fragments_path,
            )
            first = first_brain.run_cycle(
                "The blue sensor detected a high temperature.",
                "Remember the blue sensor temperature event",
            )
            episode = next(
                event.artifact for event in first.events
                if event.event_type == "memory.episode_recorded"
            )
            self.assertEqual(first_brain.fragment_memory.count(), 1)
            self.assertEqual(
                first_brain.fragment_memory.get(episode.id, record_access=False).kind,
                "episodic",
            )
            first_brain.close()

            restarted = VirtualBrain(
                brain_path,
                fragment_memory_path=fragments_path,
            )
            second = restarted.run_cycle(
                "What happened with the blue sensor temperature?",
                "Recall the blue sensor temperature event",
            )
            retrieval = next(
                event.artifact for event in second.events
                if event.event_type == "memory.retrieved"
            )
            fragment_context = retrieval.data["fragment_context"]
            self.assertTrue(fragment_context)
            self.assertTrue(
                any("blue sensor" in item["content"].lower() for item in fragment_context)
            )
            cognitive = next(
                event.artifact for event in second.events
                if event.event_type == "cognition.completed"
            )
            understanding = cognitive.data["understanding"]
            self.assertGreater(understanding["recalled_fragment_count"], 0)
            self.assertTrue(understanding["recalled_fragments"])
            self.assertEqual(restarted.fragment_memory.count(), 2)
            self.assertTrue(restarted.audit_cycle(second.cycle_id).valid)
            restarted.store.verify_integrity()
            restarted.close()

    def test_resume_does_not_duplicate_episode_fragment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brain = VirtualBrain(
                root / "brain.sqlite",
                fragment_memory_path=root / "fragments.sqlite",
            )
            cycle_id = brain.start_cycle(
                "A unique event should be mirrored once.",
                "Record the event",
            )
            paused = brain.advance(cycle_id, stop_after="memory.episode_recorded")
            self.assertIsNone(paused)
            self.assertEqual(brain.fragment_memory.count(), 1)

            result = brain.resume(cycle_id)
            self.assertEqual(result.status, "completed")
            self.assertEqual(brain.fragment_memory.count(), 1)
            self.assertTrue(brain.audit_cycle(cycle_id).valid)
            brain.close()

    def test_retrieval_feedback_is_audited_and_idempotent_per_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brain = VirtualBrain(
                root / "brain.sqlite",
                fragment_memory_path=root / "fragments.sqlite",
            )
            fragment = brain.fragment_memory.add(
                "Blue sensor temperature calibration record",
                source_uri="test://sensor-calibration",
                importance=0.4,
                confidence=0.9,
                fragment_id="sensor-calibration",
            )
            result = brain.run_cycle(
                "Recall the blue sensor temperature calibration record",
                "Use the sensor calibration information",
            )
            retrieval = next(
                event.artifact for event in result.events
                if event.event_type == "memory.retrieved"
            )
            retrieved_ids = {
                item["fragment_id"] for item in retrieval.data["fragment_context"]
            }
            self.assertIn(fragment.id, retrieved_ids)

            feedback_event = brain.apply_retrieval_feedback(
                result.cycle_id,
                {fragment.id: True},
                strength=0.2,
                feedback_id="sensor-cycle-feedback",
            )
            self.assertEqual("feedback_applied", feedback_event.data["status"])
            self.assertEqual("sensor-cycle-feedback", feedback_event.data["feedback_id"])
            self.assertTrue(feedback_event.data["results"][0]["applied"])
            action_result = next(
                event.artifact for event in result.events
                if event.event_type == "action.result"
            )
            evaluation = next(
                event.artifact for event in result.events
                if event.event_type == "evaluation.completed"
            )
            self.assertEqual(
                action_result.id,
                feedback_event.data["outcome_evidence"]["action_result_ref"],
            )
            self.assertEqual(
                evaluation.id,
                feedback_event.data["outcome_evidence"]["evaluation_ref"],
            )
            self.assertEqual(
                {retrieval.id, action_result.id, evaluation.id},
                set(feedback_event.input_refs),
            )
            self.assertIn("action_status", feedback_event.data["outcome_evidence"])
            self.assertIn("evaluation_success", feedback_event.data["outcome_evidence"])
            self.assertAlmostEqual(
                0.6,
                brain.fragment_memory.get(fragment.id, record_access=False).importance,
            )

            replay = brain.apply_retrieval_feedback(
                result.cycle_id,
                {fragment.id: True},
                strength=0.2,
                feedback_id="sensor-cycle-feedback",
            )
            self.assertEqual(feedback_event.id, replay.id)
            with self.assertRaisesRegex(ValueError, "different strength"):
                brain.apply_retrieval_feedback(
                    result.cycle_id,
                    {fragment.id: True},
                    strength=0.3,
                    feedback_id="sensor-cycle-feedback",
                )
            with self.assertRaisesRegex(ValueError, "different outcomes"):
                brain.apply_retrieval_feedback(
                    result.cycle_id,
                    {fragment.id: False},
                    strength=0.2,
                    feedback_id="sensor-cycle-feedback",
                )
            self.assertEqual(
                1,
                sum(
                    event.event_type == "memory.retrieval_feedback_applied"
                    for event in brain.store.events_for_cycle(result.cycle_id)
                ),
            )
            self.assertAlmostEqual(
                0.6,
                brain.fragment_memory.get(fragment.id, record_access=False).importance,
            )
            brain.store.verify_integrity()
            brain.close()

    def test_association_feedback_is_outcome_linked_and_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brain = VirtualBrain(
                root / "brain.sqlite",
                fragment_memory_path=root / "fragments.sqlite",
            )
            left = brain.fragment_memory.add(
                "alpha sensor calibration record",
                source_uri="test://alpha-sensor",
                fragment_id="alpha-sensor",
            )
            right = brain.fragment_memory.add(
                "beta maintenance procedure",
                source_uri="test://beta-maintenance",
                fragment_id="beta-maintenance",
            )
            brain.fragment_memory.observe_coactivation(
                [left.id, right.id], operation_id="brain-assoc-observation-1",
                context="maintenance",
            )
            brain.fragment_memory.observe_coactivation(
                [left.id, right.id], operation_id="brain-assoc-observation-2",
                context="maintenance",
            )
            result = brain.run_cycle(
                "Recall the alpha sensor calibration and beta maintenance procedure",
                "Use the alpha sensor and beta maintenance information",
            )
            retrieval = next(
                event.artifact for event in result.events
                if event.event_type == "memory.retrieved"
            )
            retrieved = {
                item["fragment_id"] for item in retrieval.data["fragment_context"]
            }
            self.assertIn(left.id, retrieved)
            self.assertIn(right.id, retrieved)

            baseline = brain.fragment_memory.association_strength(
                left.id, right.id, context="maintenance"
            )
            event = brain.apply_association_feedback(
                result.cycle_id,
                {(left.id, right.id): True},
                context="maintenance",
                strength=0.2,
                feedback_id="brain-assoc-feedback",
            )
            self.assertEqual("association_feedback_applied", event.data["status"])
            self.assertTrue(event.data["scores"][0]["applied"])
            self.assertGreater(
                brain.fragment_memory.association_strength(
                    left.id, right.id, context="maintenance"
                ),
                baseline,
            )
            action_result = next(
                item.artifact for item in result.events
                if item.event_type == "action.result"
            )
            evaluation = next(
                item.artifact for item in result.events
                if item.event_type == "evaluation.completed"
            )
            self.assertEqual(
                {retrieval.id, action_result.id, evaluation.id},
                set(event.input_refs),
            )
            replay = brain.apply_association_feedback(
                result.cycle_id,
                {(right.id, left.id): True},
                context="MAINTENANCE",
                strength=0.2,
                feedback_id="brain-assoc-feedback",
            )
            self.assertEqual(event.id, replay.id)
            self.assertEqual(
                1,
                sum(
                    item.event_type == "memory.association_feedback_applied"
                    for item in brain.store.events_for_cycle(result.cycle_id)
                ),
            )
            brain.store.verify_integrity()
            brain.close()

    def test_retrieval_feedback_requires_observed_action_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brain = VirtualBrain(
                root / "brain.sqlite",
                fragment_memory_path=root / "fragments.sqlite",
            )
            fragment = brain.fragment_memory.add(
                "Blue sensor calibration evidence",
                source_uri="test://sensor-calibration",
                importance=0.4,
                fragment_id="calibration-evidence",
            )
            cycle_id = brain.start_cycle(
                "Recall blue sensor calibration evidence",
                "Use the calibration evidence",
            )
            paused = brain.advance(cycle_id, stop_after="memory.retrieved")
            self.assertIsNone(paused)
            with self.assertRaisesRegex(
                ValueError, "requires a persisted action result and evaluation"
            ):
                brain.apply_retrieval_feedback(
                    cycle_id,
                    {fragment.id: True},
                    feedback_id="premature-feedback",
                )
            self.assertAlmostEqual(
                0.4,
                brain.fragment_memory.get(fragment.id, record_access=False).importance,
            )
            brain.close()

    def test_retrieval_feedback_rejects_fragments_not_retrieved_in_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            brain = VirtualBrain(
                root / "brain.sqlite",
                fragment_memory_path=root / "fragments.sqlite",
            )
            brain.fragment_memory.add(
                "Unrelated archived memory",
                source_uri="test://unrelated",
                importance=0.4,
                fragment_id="unrelated",
            )
            result = brain.run_cycle(
                "A completely different observation about gardening",
                "Discuss gardening",
            )
            with self.assertRaisesRegex(ValueError, "only rate fragments retrieved"):
                brain.apply_retrieval_feedback(
                    result.cycle_id,
                    {"unrelated": True},
                    feedback_id="invalid-feedback",
                )
            self.assertAlmostEqual(
                0.4,
                brain.fragment_memory.get("unrelated", record_access=False).importance,
            )
            brain.close()

    def test_fragment_memory_is_opt_in(self):
        with tempfile.TemporaryDirectory() as directory:
            brain = VirtualBrain(Path(directory) / "brain.sqlite")
            result = brain.run_cycle("No fragment store configured.", "Complete safely")
            retrieval = next(
                event.artifact for event in result.events
                if event.event_type == "memory.retrieved"
            )
            self.assertEqual(retrieval.data["fragment_context"], [])
            brain.close()


if __name__ == "__main__":
    unittest.main()
