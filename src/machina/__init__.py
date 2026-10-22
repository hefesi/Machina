"""Machina's first durable Virtual Brain core.

The package intentionally implements the architectural contracts before any
model-specific intelligence. A caller can replace cognition, agency and the
action executor without changing the durable loop.
"""

from .autonomy import AutonomyContext, AutonomyController, AutonomyDecision, AutonomyExperienceStore, GoalCandidate
from .brain import CycleAudit, CycleResult, VirtualBrain
from .contracts import Artifact, ContractError, ContractKind
from .event_store import EventStore, IntegrityError
from .fragment_memory import FragmentMemory, MemoryFragment
from .goal_store import PersistentGoalStore
from .mnn import Connection, MNN, Unit
from .mnn_adapter import MNNCognitionAdapter
from .knowledge import DuplicateKnowledgeError, KnowledgeDocument, KnowledgeHit, KnowledgeStore

__all__ = [
    "Artifact",
    "AutonomyContext",
    "AutonomyController",
    "AutonomyDecision",
    "AutonomyExperienceStore",
    "GoalCandidate",
    "PersistentGoalStore",
    "Connection",
    "ContractError",
    "ContractKind",
    "CycleAudit",
    "CycleResult",
    "EventStore",
    "FragmentMemory",
    "MemoryFragment",
    "DuplicateKnowledgeError",
    "KnowledgeDocument",
    "KnowledgeHit",
    "KnowledgeStore",
    "IntegrityError",
    "MNN",
    "MNNCognitionAdapter",
    "Unit",
    "VirtualBrain",
]
