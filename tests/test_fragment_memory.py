"""Tests for dynamic, non-destructive fragment memory."""
from __future__ import annotations

import tempfile
import unittest
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path

from machina.fragment_memory import FragmentMemory


class FragmentMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "fragments.sqlite3"
        self.memory = FragmentMemory(self.path)

    def tearDown(self) -> None:
        self.memory.close()
        self.temp_dir.cleanup()

    def test_add_and_persist_fragment_with_provenance(self) -> None:
        fragment = self.memory.add(
            "A key design decision", source_uri="project://architecture",
            importance=0.9, confidence=0.95, tags=["architecture"],
            metadata={"decision": "keep archive"},
        )
        self.assertEqual("project://architecture", fragment.source_uri)
        self.assertEqual(1, self.memory.count())
        self.memory.close()
        self.memory = FragmentMemory(self.path)
        self.assertEqual("A key design decision", self.memory.archive()[0].content)

    def test_active_view_is_bounded_without_deleting_archive(self) -> None:
        self.memory.add("Important", source_uri="local://1", importance=0.9, fragment_id="important")
        self.memory.add("Routine", source_uri="local://2", importance=0.2, fragment_id="routine")
        self.assertEqual(["important"], [item.id for item in self.memory.active(limit=1)])
        self.assertEqual(2, self.memory.count())
        self.assertEqual(2, len(self.memory.archive()))

    def test_access_reinforces_recent_relevance(self) -> None:
        self.memory.add("Frequently used", source_uri="local://a", importance=0.4, fragment_id="used")
        self.memory.add("Rarely used", source_uri="local://b", importance=0.4, fragment_id="rare")
        for _ in range(12):
            self.memory.get("used")
        self.assertEqual("used", self.memory.active(limit=1)[0].id)

    def test_pin_protects_high_importance_memory(self) -> None:
        self.memory.add("Crucial fact", source_uri="local://critical", importance=0.1, pinned=True, fragment_id="critical")
        self.memory.add("Higher unpinned", source_uri="local://other", importance=0.8, fragment_id="other")
        self.assertEqual("critical", self.memory.active(limit=1)[0].id)

    def test_reinforce_changes_importance_and_can_pin(self) -> None:
        self.memory.add("Key fact", source_uri="local://fact", importance=0.3, fragment_id="fact")
        result = self.memory.reinforce("fact", importance_delta=0.5, confidence=0.9, pin=True)
        self.assertAlmostEqual(0.8, result.importance)
        self.assertEqual(0.9, result.confidence)
        self.assertTrue(result.pinned)

    def test_recurring_coactivation_consolidates_association_after_threshold(self) -> None:
        self.memory.add("sensor calibration", source_uri="local://sensor", fragment_id="sensor")
        self.memory.add("maintenance procedure", source_uri="local://procedure", fragment_id="procedure")

        first = self.memory.observe_coactivation(
            ["sensor", "procedure"],
            context="Maintenance",
            operation_id="cycle-1",
            min_observations=2,
        )
        self.assertTrue(first["applied"])
        self.assertEqual(1, first["pairs"][0]["observations"])
        self.assertFalse(first["pairs"][0]["linked"])
        self.assertEqual((), self.memory.get("sensor", record_access=False).related_ids)

        replay = self.memory.observe_coactivation(
            ["procedure", "sensor"],
            context="maintenance",
            operation_id="cycle-1",
            min_observations=2,
        )
        self.assertFalse(replay["applied"])
        self.assertEqual(1, replay["pairs"][0]["observations"])

        second = self.memory.observe_coactivation(
            ["sensor", "procedure"],
            context="maintenance",
            operation_id="cycle-2",
            min_observations=2,
        )
        self.assertTrue(second["pairs"][0]["linked"])
        self.assertEqual(("procedure",), self.memory.get("sensor", record_access=False).related_ids)
        self.assertEqual(("sensor",), self.memory.get("procedure", record_access=False).related_ids)
        evidence = self.memory.association_evidence("procedure", "sensor")
        self.assertEqual(2, evidence["observations"])
        self.assertEqual(["maintenance"], evidence["contexts"])
        self.assertEqual(2, self.memory.count())

    def test_association_strength_grows_with_evidence_and_decays_over_time(self) -> None:
        self.memory.add("sensor calibration", source_uri="local://sensor", fragment_id="sensor")
        self.memory.add("maintenance procedure", source_uri="local://procedure", fragment_id="procedure")
        self.memory.observe_coactivation(
            ["sensor", "procedure"], operation_id="episode-1", context="maintenance"
        )
        first_strength = self.memory.association_strength("sensor", "procedure")
        self.assertAlmostEqual(1.0 - math.exp(-0.5), first_strength)

        self.memory.observe_coactivation(
            ["sensor", "procedure"], operation_id="episode-2", context="maintenance"
        )
        stronger = self.memory.association_strength("procedure", "sensor")
        self.assertGreater(stronger, first_strength)
        row = self.memory._db.execute(
            "SELECT last_observed_at FROM memory_association_evidence WHERE fragment_a = ? AND fragment_b = ?",
            ("procedure", "sensor"),
        ).fetchone()
        observed_at = datetime.fromisoformat(row["last_observed_at"])
        decayed = self.memory.association_strength(
            "sensor", "procedure",
            as_of=observed_at + timedelta(seconds=60),
            half_life_seconds=60,
        )
        self.assertAlmostEqual(stronger * 0.5, decayed)
        self.assertEqual(2, self.memory.association_evidence("sensor", "procedure")["observations"])
        self.assertGreater(self.memory.association_strength(
            "sensor", "procedure",
            as_of=observed_at + timedelta(seconds=6000),
            half_life_seconds=60,
        ), 0.0)

    def test_manual_association_keeps_legacy_strength_and_decay_config_validates(self) -> None:
        with self.assertRaises(ValueError):
            FragmentMemory(self.path, association_decay_half_life_seconds=0)
        self.memory.add("alpha", source_uri="local://alpha", fragment_id="alpha")
        self.memory.add("beta", source_uri="local://beta", fragment_id="beta")
        self.memory.link("alpha", "beta")
        self.assertEqual(1.0, self.memory.association_strength("alpha", "beta"))

    def test_coactivation_is_idempotent_and_rejects_operation_reuse(self) -> None:
        self.memory.add("alpha memory", source_uri="local://alpha", fragment_id="alpha")
        self.memory.add("beta memory", source_uri="local://beta", fragment_id="beta")
        self.memory.observe_coactivation(
            ["alpha", "beta"], operation_id="same-cycle", context="research"
        )
        with self.assertRaisesRegex(ValueError, "different coactivation"):
            self.memory.observe_coactivation(
                ["alpha", "beta"], operation_id="same-cycle", context="maintenance"
            )
        with self.assertRaises(ValueError):
            self.memory.observe_coactivation(
                ["alpha", "alpha"], operation_id="duplicate-ids"
            )
        with self.assertRaises(KeyError):
            self.memory.observe_coactivation(
                ["alpha", "missing"], operation_id="missing-fragment"
            )
        evidence = self.memory.association_evidence("alpha", "beta")
        self.assertEqual(1, evidence["observations"])

    def test_coactivation_evidence_persists_after_reopen(self) -> None:
        self.memory.add("sensor calibration", source_uri="local://sensor", fragment_id="sensor")
        self.memory.add("temperature check", source_uri="local://temperature", fragment_id="temperature")
        self.memory.observe_coactivation(
            ["sensor", "temperature"], context="maintenance", operation_id="cycle-persist"
        )
        self.memory.close()
        self.memory = FragmentMemory(self.path)
        evidence = self.memory.association_evidence("temperature", "sensor")
        self.assertEqual(1, evidence["observations"])
        self.assertEqual(["maintenance"], evidence["contexts"])
        self.assertEqual((), self.memory.get("sensor", record_access=False).related_ids)

    def test_association_evidence_is_scoped_to_context(self) -> None:
        self.memory.add("sensor calibration", source_uri="local://sensor", fragment_id="sensor")
        self.memory.add("maintenance procedure", source_uri="local://procedure", fragment_id="procedure")
        self.memory.observe_coactivation(
            ["sensor", "procedure"], operation_id="maintenance-1", context="maintenance"
        )
        self.memory.observe_coactivation(
            ["sensor", "procedure"], operation_id="maintenance-2", context="maintenance"
        )
        self.memory.observe_coactivation(
            ["sensor", "procedure"], operation_id="research-1", context="research"
        )

        maintenance = self.memory.association_strength(
            "sensor", "procedure", context="maintenance"
        )
        research = self.memory.association_strength(
            "sensor", "procedure", context="research"
        )
        unrelated = self.memory.association_strength(
            "sensor", "procedure", context="emergency"
        )
        global_strength = self.memory.association_strength("sensor", "procedure")
        self.assertGreater(maintenance, research)
        self.assertGreater(research, unrelated)
        self.assertEqual(0.0, unrelated)
        self.assertGreater(global_strength, maintenance)

    def test_contextual_recall_does_not_promote_unrelated_association(self) -> None:
        self.memory.add("sensor calibration", source_uri="local://sensor", fragment_id="sensor")
        self.memory.add("maintenance procedure torque settings", source_uri="local://maintenance", fragment_id="maintenance")
        self.memory.add("research procedure torque settings", source_uri="local://research", fragment_id="research")
        self.memory.observe_coactivation(
            ["sensor", "maintenance"], operation_id="maintenance-a", context="maintenance"
        )
        self.memory.observe_coactivation(
            ["sensor", "maintenance"], operation_id="maintenance-b", context="maintenance"
        )
        self.memory.observe_coactivation(
            ["sensor", "research"], operation_id="research-a", context="research"
        )
        self.memory.observe_coactivation(
            ["sensor", "research"], operation_id="research-b", context="research"
        )

        maintenance_ids = [item.id for item in self.memory.recall(
            "sensor calibration", context="maintenance", limit=3
        )]
        research_ids = [item.id for item in self.memory.recall(
            "sensor calibration", context="research", limit=3
        )]
        self.assertEqual("maintenance", maintenance_ids[1])
        self.assertEqual("research", research_ids[1])

    def test_associations_are_bidirectional_and_do_not_merge(self) -> None:
        self.memory.add("Cause", source_uri="local://cause", fragment_id="cause")
        self.memory.add("Effect", source_uri="local://effect", fragment_id="effect")
        self.memory.link("cause", "effect")
        self.assertEqual(("effect",), self.memory.get("cause", record_access=False).related_ids)
        self.assertEqual(("cause",), self.memory.get("effect", record_access=False).related_ids)
        self.assertEqual(2, self.memory.count())

    def test_recall_finds_lexical_matches_by_query(self) -> None:
        self.memory.add("Circuito fechado permite corrente elétrica", source_uri="local://electricity", tags=["física"], fragment_id="electricity")
        self.memory.add("Receita de bolo de chocolate", source_uri="local://recipe", fragment_id="recipe")
        results = self.memory.recall("corrente elétrica circuito")
        self.assertEqual("electricity", results[0].id)
        self.assertNotIn("recipe", [item.id for item in results])

    def test_recall_can_include_associated_context(self) -> None:
        self.memory.add("Corrente elétrica", source_uri="local://current", fragment_id="current")
        self.memory.add("Lei de Ohm relaciona tensão, intensidade e resistência", source_uri="local://ohm", fragment_id="ohm")
        self.memory.link("current", "ohm")
        results = self.memory.recall("corrente elétrica", include_related=True)
        self.assertEqual({"current", "ohm"}, {item.id for item in results})

    def test_context_feedback_changes_only_contextual_ranking(self) -> None:
        relevant = self.memory.add(
            "alpha beta task memory",
            source_uri="local://context-relevant",
            importance=0.5,
            confidence=0.5,
            fragment_id="z-relevant",
        )
        distractor = self.memory.add(
            "alpha beta task memory",
            source_uri="local://context-distractor",
            importance=0.5,
            confidence=0.5,
            fragment_id="a-distractor",
        )
        baseline = self.memory.recall("alpha beta task", limit=2)
        self.assertEqual(["a-distractor", "z-relevant"], [item.id for item in baseline])

        scores, applied = self.memory.apply_context_feedback_batch(
            {"z-relevant": True, "a-distractor": False},
            context="maintenance",
            operation_id="maintenance-feedback-1",
            strength=0.4,
        )
        self.assertTrue(applied)
        self.assertAlmostEqual(0.9, scores["z-relevant"])
        self.assertAlmostEqual(0.1, scores["a-distractor"])
        contextual = self.memory.recall("alpha beta task", limit=2, context="maintenance")
        self.assertEqual(["z-relevant", "a-distractor"], [item.id for item in contextual])

        # Another task keeps its neutral contextual scores and original tie-break.
        other_context = self.memory.recall("alpha beta task", limit=2, context="research")
        self.assertEqual(["a-distractor", "z-relevant"], [item.id for item in other_context])
        self.assertEqual(0.5, self.memory.context_importance("z-relevant", "research"))
        self.assertAlmostEqual(relevant.importance, self.memory.get("z-relevant", record_access=False).importance)
        self.assertAlmostEqual(distractor.importance, self.memory.get("a-distractor", record_access=False).importance)

        replay_scores, replay_applied = self.memory.apply_context_feedback_batch(
            {"z-relevant": True, "a-distractor": False},
            context="MAINTENANCE",
            operation_id="maintenance-feedback-1",
            strength=0.4,
        )
        self.assertFalse(replay_applied)
        self.assertEqual(scores, replay_scores)
        self.assertAlmostEqual(0.9, self.memory.context_importance("z-relevant", "maintenance"))
        with self.assertRaisesRegex(ValueError, "different context feedback"):
            self.memory.apply_context_feedback_batch(
                {"z-relevant": False},
                context="maintenance",
                operation_id="maintenance-feedback-1",
                strength=0.4,
            )

    def test_context_feedback_history_is_append_only_and_persists(self) -> None:
        self.memory.add(
            "sensor calibration",
            source_uri="local://sensor",
            fragment_id="sensor",
        )
        self.memory.apply_context_feedback_batch(
            {"sensor": True},
            context="maintenance",
            operation_id="maintenance-1",
            strength=0.2,
        )
        self.memory.apply_context_feedback_batch(
            {"sensor": False},
            context="maintenance",
            operation_id="maintenance-2",
            strength=0.1,
        )
        # Replaying an existing operation must not append another audit event.
        _, applied = self.memory.apply_context_feedback_batch(
            {"sensor": False},
            context="maintenance",
            operation_id="maintenance-2",
            strength=0.1,
        )
        self.assertFalse(applied)
        history = self.memory.context_feedback_history("sensor", "MAINTENANCE")
        self.assertEqual(2, len(history))
        self.assertEqual(["maintenance-2", "maintenance-1"], [event["operation_id"] for event in history])
        self.assertAlmostEqual(0.6, history[0]["after_score"])
        self.assertAlmostEqual(0.7, history[0]["before_score"])
        self.assertFalse(history[0]["useful"])
        self.assertAlmostEqual(0.5, history[1]["before_score"])
        self.assertAlmostEqual(0.7, history[1]["after_score"])

        self.memory.close()
        self.memory = FragmentMemory(self.path)
        persisted = self.memory.context_feedback_history("sensor", "maintenance")
        self.assertEqual(2, len(persisted))
        self.assertEqual([event["operation_id"] for event in history], [event["operation_id"] for event in persisted])
        self.assertAlmostEqual(0.6, self.memory.context_importance("sensor", "maintenance"))

    def test_context_relevance_decays_toward_neutral_without_rewriting_storage(self) -> None:
        self.memory.add(
            "sensor calibration",
            source_uri="local://sensor",
            fragment_id="sensor",
        )
        self.memory.apply_context_feedback_batch(
            {"sensor": True},
            context="maintenance",
            operation_id="decay-positive",
            strength=0.4,
        )
        stored = self.memory._db.execute(
            "SELECT score, updated_at FROM memory_context_importance WHERE fragment_id = ? AND context_key = ?",
            ("sensor", "maintenance"),
        ).fetchone()
        updated_at = datetime.fromisoformat(stored["updated_at"])
        future = updated_at + timedelta(seconds=60)

        self.assertAlmostEqual(
            0.9,
            self.memory.context_importance(
                "sensor", "maintenance", as_of=updated_at, half_life_seconds=60
            ),
        )
        self.assertAlmostEqual(
            0.7,
            self.memory.context_importance(
                "sensor", "maintenance", as_of=future, half_life_seconds=60
            ),
        )
        self.assertAlmostEqual(
            0.5,
            self.memory.context_importance(
                "sensor", "maintenance",
                as_of=updated_at + timedelta(seconds=6000), half_life_seconds=60,
            ),
            places=6,
        )
        # A read computes an effective score but never changes persisted score/time.
        after_read = self.memory._db.execute(
            "SELECT score, updated_at FROM memory_context_importance WHERE fragment_id = ? AND context_key = ?",
            ("sensor", "maintenance"),
        ).fetchone()
        self.assertEqual(float(stored["score"]), float(after_read["score"]))
        self.assertEqual(str(stored["updated_at"]), str(after_read["updated_at"]))
        self.assertAlmostEqual(0.9, self.memory.context_importance("sensor", "maintenance"))

    def test_negative_context_relevance_also_decays_toward_neutral(self) -> None:
        self.memory.add("old sensor data", source_uri="local://sensor", fragment_id="sensor")
        self.memory.apply_context_feedback_batch(
            {"sensor": False},
            context="maintenance",
            operation_id="decay-negative",
            strength=0.2,
        )
        row = self.memory._db.execute(
            "SELECT updated_at FROM memory_context_importance WHERE fragment_id = ? AND context_key = ?",
            ("sensor", "maintenance"),
        ).fetchone()
        updated_at = datetime.fromisoformat(row["updated_at"])
        self.assertAlmostEqual(
            0.4,
            self.memory.context_importance(
                "sensor", "maintenance",
                as_of=updated_at + timedelta(seconds=60), half_life_seconds=60,
            ),
        )

    def test_context_decay_configuration_is_validated_and_used_by_recall(self) -> None:
        with self.assertRaises(ValueError):
            FragmentMemory(self.path, context_decay_half_life_seconds=0)
        self.memory.add("alpha beta task", source_uri="local://one", fragment_id="one")
        self.memory.apply_context_feedback_batch(
            {"one": True}, context="maintenance",
            operation_id="decay-configured", strength=0.4,
        )
        self.memory.context_decay_half_life_seconds = 60
        row = self.memory._db.execute(
            "SELECT updated_at FROM memory_context_importance WHERE fragment_id = ? AND context_key = ?",
            ("one", "maintenance"),
        ).fetchone()
        updated_at = datetime.fromisoformat(row["updated_at"])
        # A historical as_of can be supplied to the public score API; recall
        # uses the configured half-life and a current UTC clock automatically.
        self.assertAlmostEqual(
            0.7,
            self.memory.context_importance(
                "one", "maintenance",
                as_of=updated_at + timedelta(seconds=60),
            ),
        )
        self.assertEqual(["one"], [item.id for item in self.memory.recall(
            "alpha beta task", context="maintenance"
        )])

    def test_recall_validates_query_and_limit(self) -> None:
        with self.assertRaises(ValueError):
            self.memory.recall("   ")
        with self.assertRaises(ValueError):
            self.memory.recall("memória", limit=0)

    def test_invalid_values_and_missing_ids_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.memory.add("", source_uri="local://bad")
        with self.assertRaises(ValueError):
            self.memory.add("x", source_uri="local://bad", importance=1.2)
        with self.assertRaises(ValueError):
            self.memory.active(limit=0)
        with self.assertRaises(KeyError):
            self.memory.get("missing")


if __name__ == "__main__":
    unittest.main()
