"""Machina's first durable Virtual Brain core.

The package intentionally implements the architectural contracts before any
model-specific intelligence. A caller can replace cognition, agency and the
action executor without changing the durable loop.
"""

from .brain import CycleAudit, CycleResult, VirtualBrain
from .contracts import Artifact, ContractError, ContractKind
from .event_store import EventStore, IntegrityError
from .mnn import Connection, MNN, Unit
from .mnn_adapter import MNNCognitionAdapter
from .self_model import SelfModel

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
    "MNNCognitionAdapter",
    "SelfModel",
    "Unit",
    "VirtualBrain",
]
