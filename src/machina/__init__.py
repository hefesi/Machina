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
from .mnn_action_learning import MNNActionLearner
from .mnn_agent import MNNLearningAgent
from .mnn_adapter import MNNCognitionAdapter
from .mnn_concept_review import ConceptReview, MNNConceptReviewer
from .mnn_concept_advisor import ConceptRecommendation, MNNConceptAdvisor
from .mnn_concepts import ConceptHypothesis, MNNConceptBuilder
from .mnn_contextual_outcome_policy import MNNContextualOutcomePolicy
from .mnn_experience import MNNExperienceCycle
from .mnn_memory_consolidation import ConsolidatedMemory, MNNMemoryConsolidator
from .mnn_reward import RewardModulator
from .mnn_reward_drift import MNNRewardDriftDetector
from .mnn_strategy_review import MNNStrategyReviewer
from .planning import HierarchicalPlanner, PersistentPlanStore
from .knowledge import DuplicateKnowledgeError, KnowledgeDocument, KnowledgeHit, KnowledgeStore

__all__ = [
    "Artifact", "AutonomyContext", "AutonomyController", "AutonomyDecision",
    "AutonomyExperienceStore", "GoalCandidate", "PersistentGoalStore",
    "HierarchicalPlanner", "PersistentPlanStore", "Connection", "ContractError",
    "ContractKind", "CycleAudit", "CycleResult", "EventStore", "FragmentMemory",
    "MemoryFragment", "ConsolidatedMemory", "MNNMemoryConsolidator",
    "ConceptHypothesis", "MNNConceptBuilder", "ConceptReview", "MNNConceptReviewer",
    "ConceptRecommendation", "MNNConceptAdvisor", "MNNContextualOutcomePolicy",
    "DuplicateKnowledgeError", "KnowledgeDocument", "KnowledgeHit", "KnowledgeStore",
    "IntegrityError", "MNN", "MNNActionLearner", "MNNLearningAgent", "MNNRewardDriftDetector", "MNNStrategyReviewer",
    "MNNCognitionAdapter", "MNNExperienceCycle", "RewardModulator", "Unit", "VirtualBrain",
]
