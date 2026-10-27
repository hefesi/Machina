"""End-to-end tests for concept-guided decisions and reward feedback."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from machina.fragment_memory import FragmentMemory
from machina.mnn_action_learning import MNNActionLearner
from machina.mnn_agent import MNNLearningAgent
from machina.mnn_concept_advisor import MNNConceptAdvisor
from machina.mnn_concepts import MNNConceptBuilder


class MNNConceptGuidedAgentTests(unittest.TestCase):
    def make_memory(self, memory: FragmentMemory) -> None:
        for identifier in ("e1", "e2"):
            memory.add(
                f"Evidence {identifier}", kind="fact",
                source_uri=f"test://{identifier}", tags=("stable-context",),
                confidence=0.9, metadata={"polarity": "supports"},
                fragment_id=identifier,
            )
        MNNConceptBuilder(memory, min_support=2).consolidate()

    def test_concept_guidance_selects_action_then_reward_updates_learner(self) -> None:
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            self.make_memory(memory)
            advisor = MNNConceptAdvisor(memory, {"stable-context": "pause"}, min_support=2)
            agent = MNNLearningAgent(
                MNNActionLearner(["continue", "pause"], learning_rate=0.5),
                memory, concept_advisor=advisor,
            )
            decision = agent.decide(use_concepts=True, context_tags=["stable-context"])
            self.assertEqual("pause", decision["action"])
            self.assertEqual("concept", decision["selection_source"])
            self.assertEqual("recommended", decision["concept_guidance"]["status"])
            self.assertEqual("continue", decision["fallback_action"])
            result = agent.resolve(1.0, context="stable context trial")
            self.assertEqual("pause", result["learning_update"]["action"])
            self.assertGreater(result["predictions"]["pause"], result["predictions"]["continue"])
            outcome = memory.get(result["experience_id"], record_access=False)
            self.assertEqual("pause", outcome.metadata["action"])
            self.assertEqual(1.0, outcome.metadata["reward"])

    def test_abstention_falls_back_and_requests_new_experience(self) -> None:
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            advisor = MNNConceptAdvisor(memory, {"unknown-context": "pause"}, min_support=2)
            agent = MNNLearningAgent(
                MNNActionLearner(["continue", "pause"]), memory,
                concept_advisor=advisor,
            )
            decision = agent.decide(use_concepts=True, context_tags=["unknown-context"])
            self.assertEqual("learner", decision["selection_source"])
            self.assertEqual(decision["fallback_action"], decision["action"])
            self.assertEqual("abstained", decision["concept_guidance"]["status"])
            self.assertTrue(decision["request_experience"])
            agent.resolve(0.0, context="unknown context trial")

    def test_concept_selected_pending_action_survives_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            self.make_memory(memory)
            advisor = MNNConceptAdvisor(memory, {"stable-context": "pause"}, min_support=2)
            agent = MNNLearningAgent(
                MNNActionLearner(["continue", "pause"]), memory,
                concept_advisor=advisor,
            )
            agent.decide(use_concepts=True, context_tags=["stable-context"])
            snapshot = json.loads(json.dumps(agent.snapshot()))
            restored = MNNLearningAgent.from_snapshot(snapshot, memory)
            self.assertEqual("pause", restored.pending_action)
            self.assertEqual("concept", restored.pending_action_source)
            result = restored.resolve(0.5, context="restored concept-guided trial")
            self.assertEqual("pause", result["learning_update"]["action"])

    def test_concept_mode_requires_configured_advisor_and_tags(self) -> None:
        with tempfile.TemporaryDirectory() as directory, FragmentMemory(Path(directory) / "m.db") as memory:
            agent = MNNLearningAgent(MNNActionLearner(["continue", "pause"]), memory)
            with self.assertRaises(ValueError):
                agent.decide(use_concepts=True, context_tags=["x"])
            advisor = MNNConceptAdvisor(memory, {"x": "pause"})
            configured = MNNLearningAgent(
                MNNActionLearner(["continue", "pause"]), memory,
                concept_advisor=advisor,
            )
            with self.assertRaises(ValueError):
                configured.decide(use_concepts=True)
            with self.assertRaises(ValueError):
                configured.decide(context_tags=["x"])
            self.assertEqual(0, configured.learner.decisions)
            with self.assertRaises(ValueError):
                configured.decide(use_concepts=True, context_tags=[""])
            self.assertEqual(0, configured.learner.decisions)


if __name__ == "__main__":
    unittest.main()
