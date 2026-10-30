import unittest

from machina.chemical_signaling import ChemicalEvent, ChemicalParameters, ChemicalSignaling, ChemicalState


class ChemicalSignalingTests(unittest.TestCase):
    def test_step_is_deterministic_and_advances_time(self):
        a, b = ChemicalSignaling(), ChemicalSignaling()
        event = ChemicalEvent(reward=0.9, novelty=0.8, uncertainty=0.3, progress=0.7)
        self.assertEqual(a.step(event), b.step(event))
        self.assertEqual(a.snapshot(), b.snapshot())
        self.assertEqual(a.state.timestep, 1)

    def test_all_concentrations_remain_bounded(self):
        system = ChemicalSignaling()
        event = ChemicalEvent(reward=1, novelty=1, uncertainty=1, effort=1, progress=1, risk=1)
        for _ in range(100):
            system.step(event)
        for name in ("dopamine", "acetylcholine", "noradrenaline", "serotonin"):
            self.assertGreaterEqual(getattr(system.state, name), 0)
            self.assertLessEqual(getattr(system.state, name), 1)

    def test_prediction_error_sign(self):
        system = ChemicalSignaling()
        self.assertGreater(system.step(ChemicalEvent(reward=1.0)).prediction_error, 0)
        self.assertLess(system.step(ChemicalEvent(reward=0.0)).prediction_error, 0)

    def test_novelty_increases_attention_and_exploration(self):
        familiar = ChemicalSignaling().step(ChemicalEvent())
        novel = ChemicalSignaling().step(ChemicalEvent(novelty=1.0, uncertainty=0.8))
        self.assertGreater(novel.attention_gain, familiar.attention_gain)
        self.assertGreater(novel.exploration_drive, familiar.exploration_drive)


    def test_internal_motivational_pressure_increases_exploration_and_alertness(self):
        baseline = ChemicalSignaling().step(ChemicalEvent())
        pressured = ChemicalSignaling().step(
            ChemicalEvent(motivational_pressure=1.0)
        )
        self.assertGreater(pressured.exploration_drive, baseline.exploration_drive)
        self.assertGreater(
            pressured.concentrations["acetylcholine"],
            baseline.concentrations["acetylcholine"],
        )
        self.assertGreater(
            pressured.concentrations["noradrenaline"],
            baseline.concentrations["noradrenaline"],
        )

    def test_snapshot_round_trip(self):
        system = ChemicalSignaling()
        system.step(ChemicalEvent(reward=0.8, novelty=0.4))
        self.assertEqual(ChemicalSignaling.from_snapshot(system.snapshot()).snapshot(), system.snapshot())

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            ChemicalEvent(novelty=2.0)
        with self.assertRaises(ValueError):
            ChemicalEvent(reward=float("nan"))
        with self.assertRaises(ValueError):
            ChemicalParameters(dopamine_decay=-0.1)
        with self.assertRaises(ValueError):
            ChemicalState(dopamine=1.5)

    def test_unknown_snapshot_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            ChemicalState.from_snapshot({"dopamine": 0.0, "mystery": 1})


if __name__ == "__main__":
    unittest.main()
