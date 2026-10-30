import unittest

from machina.self_regulation import RegulationProposal
from machina.temporal_regulation import TemporalRegulationFilter


class TemporalRegulationFilterTests(unittest.TestCase):
    def proposal(self, value):
        return RegulationProposal(
            cycle_id="c1", adjustments={"focus": value},
            metric_errors={"attention_gain": value},
            rationale=("measured",), evidence_refs=("step:1",),
        )

    def test_smooths_successive_adjustments_and_tracks_time(self):
        regulator = TemporalRegulationFilter(alpha=0.5, deadband=0.0)
        first = regulator.filter(self.proposal(0.2))
        second = regulator.filter(self.proposal(-0.2))
        self.assertAlmostEqual(0.1, first.adjustments["focus"])
        self.assertAlmostEqual(-0.05, second.adjustments["focus"])
        self.assertEqual(2, regulator.timestep)
        self.assertIn("temporal_filter", second.rationale[-1])

    def test_snapshot_restart_preserves_next_result(self):
        regulator = TemporalRegulationFilter(alpha=0.4)
        regulator.filter(self.proposal(0.15))
        restored = TemporalRegulationFilter.from_snapshot(regulator.snapshot())
        expected = regulator.filter(self.proposal(-0.1))
        actual = restored.filter(self.proposal(-0.1))
        self.assertEqual(expected.adjustments, actual.adjustments)
        self.assertEqual(regulator.snapshot(), restored.snapshot())

    def test_deadband_suppresses_small_residual(self):
        regulator = TemporalRegulationFilter(alpha=1.0, deadband=0.02)
        result = regulator.filter(self.proposal(0.01))
        self.assertEqual(0.0, result.adjustments["focus"])

    def test_invalid_proposal_does_not_advance_state(self):
        regulator = TemporalRegulationFilter()
        with self.assertRaises(ValueError):
            regulator.filter(self.proposal(0.5))
        self.assertEqual(0, regulator.timestep)
        self.assertEqual({}, regulator.snapshot()["smoothed"])

    def test_snapshot_validation(self):
        with self.assertRaises(ValueError):
            TemporalRegulationFilter.from_snapshot({"schema_version": 99})


if __name__ == "__main__":
    unittest.main()
