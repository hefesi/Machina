import unittest

from machina.mnn_motivation import (
    MotivationalConflict,
    MotivationalCooperation,
    MotivationalDrive,
    MotivationSystem,
)


class MotivationSystemTests(unittest.TestCase):
    def make_system(self):
        return MotivationSystem([
            MotivationalDrive("curiosity", level=0.8, setpoint=0.8, priority=0.7),
            MotivationalDrive("stability", level=0.6, setpoint=0.6, priority=1.0),
        ])

    def test_priority_weighted_urgency_ranks_drives_deterministically(self):
        system = self.make_system()
        self.assertEqual("stability", system.ranked_drives()[0][0])
        self.assertAlmostEqual(0.6, system.ranked_drives()[0][1])

    def test_fulfillment_reduces_deficit_and_changes_priority(self):
        system = self.make_system()
        before = dict(system.ranked_drives())
        after = system.step({"stability": 1.0})
        self.assertLess(after["stability"], before["stability"])
        self.assertEqual(1, system.timestep)

    def test_unfulfilled_drive_recovers_toward_setpoint(self):
        system = MotivationSystem([
            MotivationalDrive("curiosity", level=0.1, setpoint=0.9, recovery_rate=0.5)
        ])
        system.step()
        self.assertAlmostEqual(0.5, system.drives["curiosity"].level)

    def test_unknown_or_invalid_outcome_does_not_mutate_state(self):
        system = self.make_system()
        before = system.snapshot()
        with self.assertRaises(ValueError):
            system.step({"unknown": 1.0})
        self.assertEqual(before, system.snapshot())
        with self.assertRaises(ValueError):
            system.step({"curiosity": float("nan")})
        self.assertEqual(before, system.snapshot())

    def test_urgency_maps_to_bounded_autonomy_goal_feedback(self):
        system = MotivationSystem([
            MotivationalDrive("curiosity", level=1.0, priority=1.0),
            MotivationalDrive("stability", level=0.0, priority=1.0),
            MotivationalDrive("neutral", level=0.5, priority=1.0),
        ])
        adjustments = system.autonomy_adjustments()
        self.assertAlmostEqual(0.15, adjustments["curiosity"])
        self.assertAlmostEqual(-0.15, adjustments["stability"])
        self.assertAlmostEqual(0.0, adjustments["neutral"])
        with self.assertRaises(ValueError):
            system.autonomy_adjustments(gain=0.5)

    def test_aggregate_chemical_pressure_tracks_mean_drive_urgency(self):
        system = MotivationSystem([
            MotivationalDrive("curiosity", level=1.0, priority=1.0),
            MotivationalDrive("stability", level=0.0, priority=1.0),
        ])
        self.assertAlmostEqual(0.5, system.chemical_pressure)
        system.step({"stability": 1.0})
        self.assertLess(system.chemical_pressure, 0.5)
        self.assertGreaterEqual(system.chemical_pressure, 0.0)
        self.assertLessEqual(system.chemical_pressure, 1.0)

    def test_snapshot_round_trip_preserves_future_dynamics(self):
        system = self.make_system()
        system.step({"curiosity": 0.4})
        restored = MotivationSystem.from_snapshot(system.snapshot())
        self.assertEqual(system.snapshot(), restored.snapshot())
        self.assertEqual(system.step(), restored.step())
        self.assertEqual(system.snapshot(), restored.snapshot())


    def test_temporal_pressure_accumulates_and_releases_gradually(self):
        drive = MotivationalDrive(
            "curiosity", level=1.0, setpoint=1.0, priority=1.0,
            relief_gain=1.0, persistence=0.75,
        )
        system = MotivationSystem([drive])
        self.assertAlmostEqual(1.0, system.temporal_urgencies()["curiosity"])
        system.step({"curiosity": 1.0})
        after_relief = system.temporal_urgencies()["curiosity"]
        self.assertGreater(after_relief, 0.0)
        self.assertLess(after_relief, 1.0)
        system.step({"curiosity": 1.0})
        self.assertLess(system.temporal_urgencies()["curiosity"], after_relief)

    def test_zero_persistence_tracks_effective_urgency_immediately(self):
        system = MotivationSystem([
            MotivationalDrive("a", level=0.9, persistence=0.0),
            MotivationalDrive("b", level=0.2, persistence=0.0),
        ], [MotivationalConflict("a", "b", 0.5)])
        effective = system.step()
        self.assertEqual(effective, system.temporal_urgencies())

    def test_temporal_pressure_persists_and_restores_future_dynamics(self):
        system = MotivationSystem([
            MotivationalDrive("a", level=0.9, persistence=0.6),
            MotivationalDrive("b", level=0.2, persistence=0.3),
        ], [MotivationalConflict("a", "b", 0.4)])
        system.step()
        restored = MotivationSystem.from_snapshot(system.snapshot())
        self.assertEqual(system.snapshot(), restored.snapshot())
        self.assertEqual(system.step(), restored.step())
        self.assertEqual(system.temporal_urgencies(), restored.temporal_urgencies())

    def test_temporal_ranking_is_deterministic(self):
        system = MotivationSystem([
            MotivationalDrive("slow", level=0.8, persistence=0.9),
            MotivationalDrive("fast", level=0.2, persistence=0.0),
        ])
        system.step({"slow": 1.0})
        self.assertEqual(sorted(system.temporal_urgencies().items(), key=lambda item: (-item[1], item[0])),
                         system.ranked_temporal_drives())

    def test_rejects_duplicate_drive_and_invalid_parameters(self):
        with self.assertRaises(ValueError):
            MotivationalDrive("bad_persistence", persistence=1.1)
        with self.assertRaises(ValueError):
            MotivationSystem([MotivationalDrive("same"), MotivationalDrive("same")])
        with self.assertRaises(ValueError):
            MotivationalDrive("bad", priority=-1)

    def test_conflict_inhibits_competing_drive_without_mutating_raw_deficit(self):
        system = MotivationSystem(
            [
                MotivationalDrive("explore", level=0.9),
                MotivationalDrive("rest", level=0.7),
                MotivationalDrive("create", level=0.8),
            ],
            [MotivationalConflict("explore", "rest", strength=0.8)],
            conflict_gain=0.5,
        )
        raw = {name: drive.urgency for name, drive in system.drives.items()}
        effective = system.effective_urgencies()
        self.assertAlmostEqual(0.55, effective["explore"])
        self.assertAlmostEqual(0.25, effective["rest"])
        self.assertAlmostEqual(0.8, effective["create"])
        self.assertEqual(raw, {name: drive.urgency for name, drive in system.drives.items()})

    def test_conflict_arbitration_is_independent_of_registration_order(self):
        drives = [
            MotivationalDrive("a", level=0.9),
            MotivationalDrive("b", level=0.7),
            MotivationalDrive("c", level=0.4),
        ]
        first = MotivationSystem(
            drives,
            [MotivationalConflict("a", "b", 0.8), MotivationalConflict("a", "c", 0.2)],
        )
        second = MotivationSystem(
            list(reversed([MotivationalDrive("a", level=0.9), MotivationalDrive("b", level=0.7), MotivationalDrive("c", level=0.4)])),
            [MotivationalConflict("a", "c", 0.2), MotivationalConflict("a", "b", 0.8)],
        )
        self.assertEqual(first.effective_urgencies(), second.effective_urgencies())

    def test_conflicts_validate_references_duplicates_and_self_edges(self):
        with self.assertRaises(ValueError):
            MotivationalConflict("same", "same")
        system = self.make_system()
        with self.assertRaises(ValueError):
            system.add_conflict(MotivationalConflict("curiosity", "missing"))
        system.add_conflict(MotivationalConflict("curiosity", "stability"))
        with self.assertRaises(ValueError):
            system.add_conflict(MotivationalConflict("stability", "curiosity"))

    def test_conflicts_persist_and_legacy_schema_one_remains_readable(self):
        system = MotivationSystem(
            [MotivationalDrive("a", level=0.8), MotivationalDrive("b", level=0.6)],
            [MotivationalConflict("a", "b", 0.7)],
        )
        restored = MotivationSystem.from_snapshot(system.snapshot())
        self.assertEqual(system.snapshot(), restored.snapshot())
        legacy = {
            "schema_version": 1,
            "timestep": 2,
            "drives": [MotivationalDrive("legacy", level=0.4).snapshot()],
        }
        self.assertEqual(0.4, MotivationSystem.from_snapshot(legacy).effective_urgencies()["legacy"])


    def test_cooperation_boosts_partner_urgency_without_changing_raw_drive(self):
        system = MotivationSystem(
            [
                MotivationalDrive("curiosity", level=0.8),
                MotivationalDrive("creation", level=0.4),
                MotivationalDrive("rest", level=0.2),
            ],
            cooperations=[MotivationalCooperation("curiosity", "creation", 0.8)],
            cooperation_gain=0.25,
        )
        effective = system.effective_urgencies()
        self.assertAlmostEqual(0.88, effective["curiosity"])
        self.assertAlmostEqual(0.6, effective["creation"])
        self.assertAlmostEqual(0.2, effective["rest"])
        self.assertAlmostEqual(0.8, system.drives["curiosity"].urgency)

    def test_cooperation_is_symmetric_and_registration_order_independent(self):
        a = MotivationSystem(
            [MotivationalDrive("a", level=0.8), MotivationalDrive("b", level=0.4)],
            cooperations=[MotivationalCooperation("a", "b", 0.6)],
        )
        b = MotivationSystem(
            [MotivationalDrive("b", level=0.4), MotivationalDrive("a", level=0.8)],
            cooperations=[MotivationalCooperation("b", "a", 0.6)],
        )
        self.assertEqual(a.effective_urgencies(), b.effective_urgencies())
        self.assertGreater(a.effective_urgencies()["a"], a.drives["a"].urgency)
        self.assertGreater(a.effective_urgencies()["b"], a.drives["b"].urgency)

    def test_conflict_and_cooperation_on_same_pair_are_rejected(self):
        system = MotivationSystem(
            [MotivationalDrive("a"), MotivationalDrive("b")],
            [MotivationalConflict("a", "b")],
        )
        with self.assertRaises(ValueError):
            system.add_cooperation(MotivationalCooperation("a", "b"))

    def test_cooperation_validates_and_persists_with_schema_three(self):
        with self.assertRaises(ValueError):
            MotivationalCooperation("a", "a")
        system = MotivationSystem(
            [MotivationalDrive("a", level=0.8), MotivationalDrive("b", level=0.6)],
            cooperations=[MotivationalCooperation("a", "b", 0.7)],
            cooperation_gain=0.2,
        )
        restored = MotivationSystem.from_snapshot(system.snapshot())
        self.assertEqual(4, system.snapshot()["schema_version"])
        self.assertEqual(system.snapshot(), restored.snapshot())
        self.assertEqual(system.step(), restored.step())

    def test_schema_two_snapshot_remains_compatible(self):
        legacy = {
            "schema_version": 2,
            "timestep": 1,
            "drives": [MotivationalDrive("legacy", level=0.4).snapshot()],
            "conflicts": [],
            "conflict_gain": 0.5,
        }
        restored = MotivationSystem.from_snapshot(legacy)
        self.assertEqual(0.4, restored.effective_urgencies()["legacy"])
        self.assertEqual([], restored.snapshot()["cooperations"])


if __name__ == "__main__":
    unittest.main()
