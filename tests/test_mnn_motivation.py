import unittest

from machina.mnn_motivation import MotivationalDrive, MotivationSystem


class MotivationSystemTests(unittest.TestCase):
    def make_system(self):
        return MotivationSystem([
            MotivationalDrive("curiosity", level=0.8, setpoint=0.8, priority=0.7),
            MotivationalDrive("stability", level=0.6, setpoint=0.6, priority=1.0),
        ])

    def test_priority_weighted_urgency_ranks_drives_deterministically(self):
        system = self.make_system()
        self.assertEqual("stability", system.ranked_drives()[0][0])
        self.assertAlmostEqual(0.8, system.ranked_drives()[0][1])

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

    def test_snapshot_round_trip_preserves_future_dynamics(self):
        system = self.make_system()
        system.step({"curiosity": 0.4})
        restored = MotivationSystem.from_snapshot(system.snapshot())
        self.assertEqual(system.snapshot(), restored.snapshot())
        self.assertEqual(system.step(), restored.step())
        self.assertEqual(system.snapshot(), restored.snapshot())

    def test_rejects_duplicate_drive_and_invalid_parameters(self):
        with self.assertRaises(ValueError):
            MotivationSystem([MotivationalDrive("same"), MotivationalDrive("same")])
        with self.assertRaises(ValueError):
            MotivationalDrive("bad", priority=-1)


if __name__ == "__main__":
    unittest.main()
