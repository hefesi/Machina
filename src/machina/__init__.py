"""Machina's first durable Virtual Brain core.

The package intentionally implements the architectural contracts before any
model-specific intelligence.  A caller can replace cognition, agency and the
action executor without changing the durable loop.
"""

from .brain import CycleAudit, CycleResult, VirtualBrain
from .contracts import Artifact, ContractError, ContractKind
from .event_store import EventStore, IntegrityError

__all__ = [
    "Artifact",
    "ContractError",
    "ContractKind",
    "CycleAudit",
    "CycleResult",
    "EventStore",
    "IntegrityError",
    "VirtualBrain",
]
