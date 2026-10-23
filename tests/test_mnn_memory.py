import unittest

from machina.mnn_memory import MemoryFragment, PriorityMemory


class PriorityMemoryTests(unittest.TestCase):
    def test_retrieval_prefers_relevant_and_reinforces_fragment(self):
        memory = PriorityMemory()
        memory.remember(MemoryFragment("a", "MNN connection plasticity", importance=0.8, strength=0.5))
        memory.remember(MemoryFragment("b", "cooking recipes", importance=1.0))
        results = memory.retrieve("MNN plasticity", limit=1)
        self.assertEqual([fragment.id for fragment in results], ["a"])
        self.assertEqual(results[0].access_count, 1)
        self.assertGreater(results[0].strength, 0.5)

    def test_decay_is_slower_for_important_fragments(self):
        memory = PriorityMemory()
        memory.remember(MemoryFragment("low", "low priority", importance=0.1, strength=1.0))
        memory.remember(MemoryFragment("high", "high priority", importance=0.9, strength=1.0))
        changes = memory.decay(rate=0.2, steps=1)
        self.assertLess(changes["low"], changes["high"])
        self.assertEqual(memory.fragments["high"].strength, 0.98)

    def test_protected_fragment_survives_decay_pruning_and_capacity(self):
        memory = PriorityMemory(capacity=2)
        memory.remember(MemoryFragment("protected", "core rule", importance=0.99, strength=0.1, protected=True))
        memory.remember(MemoryFragment("weak", "temporary note", importance=0.1, strength=0.1))
        memory.decay(rate=1.0, steps=5)
        self.assertEqual(memory.fragments["protected"].strength, 0.1)
        self.assertNotIn("protected", memory.prune(min_priority=1.0))
        memory.remember(MemoryFragment("new", "new information", importance=0.5))
        self.assertIn("protected", memory.fragments)
        self.assertEqual(len(memory.fragments), 2)

    def test_snapshot_round_trip(self):
        memory = PriorityMemory(capacity=7, retention_floor=0.02)
        memory.remember(MemoryFragment("x", "persist this", importance=0.7, tags=("memory", "test")))
        memory.retrieve("persist")
        restored = PriorityMemory.from_snapshot(memory.snapshot())
        self.assertEqual(restored.snapshot(), memory.snapshot())

    def test_rejects_invalid_values(self):
        with self.assertRaises(ValueError):
            MemoryFragment("x", "bad importance", importance=2)
        with self.assertRaises(ValueError):
            PriorityMemory(capacity=0)
        with self.assertRaises(ValueError):
            PriorityMemory().decay(rate=-0.1)


if __name__ == "__main__":
    unittest.main()
