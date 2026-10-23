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
