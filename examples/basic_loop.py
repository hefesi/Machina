"""Run with: PYTHONPATH=src python3 examples/basic_loop.py"""

from pathlib import Path

from machina import VirtualBrain


database = Path("machina-brain.sqlite")
with VirtualBrain(database) as brain:
    result = brain.run_cycle(
        "The user asked for a durable Virtual Brain foundation.",
        "Register the observation and close one safe cognitive loop.",
        success_criteria=["The observation is preserved with provenance."],
    )
    print(f"cycle: {result.cycle_id}")
    print(f"status: {result.status}")
    print("events:")
    for event in result.events:
        print(f"  {event.sequence:02d} {event.event_type} ({event.artifact.id})")
    brain.store.verify_integrity()
