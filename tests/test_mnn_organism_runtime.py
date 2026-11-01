from __future__ import annotations

import unittest

from machina import (
    MNN,
    MNNOrganism,
    MotivationalDrive,
    MotivationSystem,
    Unit,
    build_mnn_organism_runtime,
)


class MNNOrganismRuntimeTests(unittest.TestCase):
    def make_organism(self) -> MNNOrganism:
        network = MNN()
        network.add_unit(Unit("sensor", activation="identity"))
        network.add_unit(Unit("memory", activation="tanh"))
        motivation = MotivationSystem(drives=[
            MotivationalDrive("curiosity", level=0.9, setpoint=0.2),
            MotivationalDrive("stability", level=0.3, setpoint=0.2),
        ])
        return MNNOrganism(
            "runtime-test",
            network=network,
            motivation=motivation,
            learning_rate=0.0,
        )

    def test_factory_wires_both_adapters_to_same_organism(self):
        organism = self.make_organism()
        runtime = build_mnn_organism_runtime(
            organism,
            input_features={"sensor": "text_length"},
            target_unit="memory",
        )
        self.assertIs(runtime.organism, organism)
        self.assertIs(runtime.cognition.organism, organism)
        self.assertIs(runtime.agency.organism, organism)
        self.assertIs(runtime.motivation, organism.motivation)

    def test_motivation_is_exposed_as_bounded_goal_adjustments(self):
        runtime = build_mnn_organism_runtime(
            self.make_organism(),
            input_features={"sensor": "text_length"},
            target_unit="memory",
        )
        adjustments = runtime.drive_adjustments()
        self.assertIn("curiosity", adjustments)
        self.assertIn("stability", adjustments)
        self.assertTrue(all(-0.3 <= value <= 0.3 for value in adjustments.values()))
        self.assertEqual(runtime.ranked_drives()[0][0], "curiosity")

    def test_runtime_without_motivation_returns_empty_signals(self):
        organism = MNNOrganism("runtime-no-motivation", network=MNN())
        runtime = build_mnn_organism_runtime(
            organism,
            input_features={"unit_0": "text_length"},
            target_unit="unit_0",
        )
        self.assertIsNone(runtime.motivation)
        self.assertEqual(runtime.drive_adjustments(), {})
        self.assertEqual(runtime.ranked_drives(), [])

    def test_factory_rejects_non_organism(self):
        with self.assertRaises(TypeError):
            build_mnn_organism_runtime(
                object(),
                input_features={"sensor": "text_length"},
                target_unit="sensor",
            )


if __name__ == "__main__":
    unittest.main()
