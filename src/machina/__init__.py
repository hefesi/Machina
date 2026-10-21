"""Machina's first durable Virtual Brain core.

The package intentionally implements the architectural contracts before any
model-specific intelligence.  A caller can replace cognition, agency and the
action executor without changing the durable loop.
"""

from .brain import CycleAudit, CycleResult, VirtualBrain
from .contracts import Artifact, ContractError, ContractKind
from .event_store import EventStore, IntegrityError
from .mnn import Connection, MNN, Unit

__all__ = [
    "Artifact",
    "Connection",
    "ContractError",
    "ContractKind",
    "CycleAudit",
    "CycleResult",
    "EventStore",
    "IntegrityError",
    "MNN",
    "Unit",
    "VirtualBrain",
]
