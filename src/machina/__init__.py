"""Machina's first durable Virtual Brain core.

The package intentionally implements the architectural contracts before any
model-specific intelligence. A caller can replace cognition, agency and the
action executor without changing the durable loop.
"""

from .autonomy import AutonomyContext, AutonomyController, AutonomyDecision, AutonomyExperienceStore, GoalCandidate
from .brain import CycleAudit, CycleResult, VirtualBrain
from .contracts import Artifact, ContractError, ContractKind
from .chemical_signaling import ChemicalEvent, ChemicalParameters, ChemicalSignaling, ChemicalState, ChemicalUpdate
from .event_store import EventStore, IntegrityError
from .fragment_memory import FragmentMemory, MemoryFragment
from .mnn_memory_reconsolidation import MemoryRevisionProposal, MNNMemoryReconsolidationPipeline
from .mnn_memory_conflict import MemoryConflictReview, MNNMemoryConflictReviewer
from .mnn_concept_relations import ConceptRelation, MNNConceptRelationStore
from .goal_store import PersistentGoalStore
from .goal_review import GoalReview, GoalReviewer
from .goal_constraints import GoalConflictResolver, GoalConstraintAssessment, GoalSchedule
from .adaptive_planning import AdaptivePlanReviewer, PlanRevision
from .goal_outcome_learning import GoalOutcomeLearner
from .experience_memory import ExperienceMemoryStore
from .strategy_self_review import StrategySelfReviewStore
from .curiosity import CuriosityInvestigationStore
from .deliberation import DeliberationDecision, InternalDeliberator
from .mnn import Connection, MNN, Unit
from .mnn_motivation import MotivationalDrive, MotivationSystem
from .mnn_organism import (DecisionAssessment, DecisionOption, MNNOrganism, MemoryGuidance, OrganismStep)
from .mnn_adapter import MNNCognitionAdapter
from .mnn_organism_adapter import MNNOrganismCognitionAdapter
from .mnn_organism_agency import MNNOrganismAgencyAdapter
from .self_model import SelfModel
from .self_state_dynamics import SelfStateDynamicsAnalyzer, SelfStateTransition
from .self_history_influence import SelfHistoryInfluence, SelfHistoryInfluenceAdapter, SelfHistoryRule
from .self_autobiographical_recall import SelfAutobiographicalMatch, SelfAutobiographicalRecall
from .self_autobiographical_evaluation import SelfExperienceAssessment, SelfAutobiographicalEvaluation, SelfAutobiographicalEvaluator
from .self_model_learning import SelfModelLearningBridge
from .self_autobiography import SelfAutobiography
from .self_transformation import SelfTransformationTracker
from .self_experience_integration import SelfExperienceIntegrator
from .self_influence import SelfInfluence, SelfInfluenceAdapter
from .self_observer import MNNStateSelfObserver
from .self_regulation import RegulationProposal, SelfRegulationController
from .temporal_regulation import TemporalRegulationFilter
from .homeostasis import HomeostaticProposal, HomeostaticRegulator, HomeostaticRule
from .homeostatic_learning import HomeostaticFeedbackLearner, HomeostaticLearningEstimate
from .mnn_reward import RewardModulator
from .planning import HierarchicalPlanner, PersistentPlanStore
from .knowledge import DuplicateKnowledgeError, KnowledgeDocument, KnowledgeHit, KnowledgeStore
from .mnn_action_learning import MNNActionLearner
from .mnn_agent import MNNLearningAgent
from .mnn_concept_review import ConceptReview, MNNConceptReviewer
from .mnn_knowledge_lifecycle import MNNKnowledgeLifecycle, MNNKnowledgeLifecycleResult
from .mnn_knowledge_use_feedback import KnowledgeUseFeedbackResult, MNNKnowledgeUseFeedback
from .mnn_concept_advisor import ConceptRecommendation, MNNConceptAdvisor
from .mnn_concepts import ConceptHypothesis, MNNConceptBuilder
from .mnn_contextual_outcome_policy import MNNContextualOutcomePolicy
from .mnn_experience import MNNExperienceCycle
from .mnn_autobiographical_learning import AutobiographicalLearningSignal, MNNAutobiographicalLearningAdvisor
from .mnn_autobiographical_consolidation import MNNAutobiographicalConsolidationAdapter
from .mnn_memory_consolidation import ConsolidatedMemory, MNNMemoryConsolidator
from .mnn_reward_drift import MNNRewardDriftDetector
from .mnn_strategy_review import MNNStrategyReviewer
from .mnn_strategy_experiment import MNNStrategyExperimentLog
from .mnn_strategy_evaluation import MNNStrategyExperimentEvaluator
from .mnn_strategy_context_memory import MNNStrategyContextMemory
from .mnn_strategy_decision_advisor import MNNStrategyDecisionAdvisor
from .mnn_strategy_feedback import MNNStrategyFeedbackAdapter, StrategyFeedback, StrategyLearningResult
from .mnn_strategy_learning_cycle import MNNStrategyLearningCycle
from .mnn_strategy_outcome_journal import MNNStrategyOutcomeJournal
from .mnn_strategy_event_bridge import MNNStrategyEventBridge
from .mnn_event_memory_projector import MNNEventMemoryProjector, MNNEventProjectionResult
from .mnn_autobiographical_recall import MNNAutobiographicalEpisode, MNNAutobiographicalRecall
from .mnn_autobiographical_strategy_advisor import MNNAutobiographicalStrategyAdvisor
from .mnn_synaptic_consolidation import MNNSynapticConsolidator
from .mnn_short_term_plasticity import MNNShortTermPlasticity
from .mnn_plasticity_control import MNNPlasticityController, MNNPlasticityProposal
from .mnn_experience_plasticity_advisor import MNNExperiencePlasticityAdvisor, MNNExperiencePlasticityProposal

__all__ = [
    "Artifact",
    "ChemicalEvent",
    "ChemicalParameters",
    "ChemicalSignaling",
    "ChemicalState",
    "ChemicalUpdate",
    "AutonomyContext",
    "AutonomyController",
    "AutonomyDecision",
    "AutonomyExperienceStore",
    "GoalCandidate",
    "PersistentGoalStore",
    "GoalReview",
    "GoalReviewer",
    "GoalConflictResolver",
    "GoalConstraintAssessment",
    "GoalSchedule",
    "AdaptivePlanReviewer",
    "PlanRevision",
    "GoalOutcomeLearner",
    "ExperienceMemoryStore",
    "StrategySelfReviewStore",
    "CuriosityInvestigationStore",
    "DeliberationDecision",
    "InternalDeliberator",
    "HierarchicalPlanner",
    "PersistentPlanStore",
    "Connection",
    "ContractError",
    "ContractKind",
    "CycleAudit",
    "CycleResult",
    "EventStore",
    "FragmentMemory",
    "MemoryFragment",
    "MemoryRevisionProposal",
    "MNNMemoryReconsolidationPipeline",
    "MemoryConflictReview",
    "MNNMemoryConflictReviewer",
    "ConceptRelation",
    "MNNConceptRelationStore",
    "DuplicateKnowledgeError",
    "KnowledgeDocument",
    "KnowledgeHit",
    "KnowledgeStore",
    "IntegrityError",
    "MNN",
    "MotivationalDrive",
    "MotivationSystem",
    "MNNOrganism",
    "MemoryGuidance",
    "DecisionOption",
    "DecisionAssessment",
    "OrganismStep",
    "MNNCognitionAdapter",
    "MNNOrganismCognitionAdapter",
    "MNNOrganismAgencyAdapter",
    "SelfModel",
    "SelfStateDynamicsAnalyzer",
    "SelfStateTransition",
    "SelfHistoryInfluence",
    "SelfHistoryInfluenceAdapter",
    "SelfHistoryRule",
    "SelfAutobiographicalMatch",
    "SelfAutobiographicalRecall",
    "SelfAutobiographicalAssessment",
    "SelfAutobiographicalEvaluation",
    "SelfAutobiographicalEvaluator",
    "SelfModelLearningBridge",
    "SelfAutobiography",
    "SelfTransformationTracker",
    "SelfExperienceIntegrator",
    "SelfInfluence",
    "SelfInfluenceAdapter",
    "MNNStateSelfObserver",
    "RegulationProposal",
    "SelfRegulationController",
    "TemporalRegulationFilter",
    "HomeostaticProposal",
    "HomeostaticRegulator",
    "HomeostaticRule",
    "HomeostaticFeedbackLearner",
    "HomeostaticLearningEstimate",
    "RewardModulator",
    "Unit",
    "VirtualBrain",
    "ConsolidatedMemory",
    "MNNMemoryConsolidator",
    "ConceptHypothesis",
    "MNNConceptBuilder",
    "ConceptReview",
    "MNNConceptReviewer",
    "MNNKnowledgeLifecycle",
    "MNNKnowledgeLifecycleResult",
    "KnowledgeUseFeedbackResult",
    "MNNKnowledgeUseFeedback",
    "ConceptRecommendation",
    "MNNConceptAdvisor",
    "MNNContextualOutcomePolicy",
    "MNNActionLearner",
    "MNNLearningAgent",
    "MNNRewardDriftDetector",
    "MNNStrategyReviewer",
    "MNNStrategyExperimentLog",
    "MNNStrategyExperimentEvaluator",
    "MNNStrategyContextMemory",
    "MNNStrategyDecisionAdvisor",
    "MNNStrategyFeedbackAdapter",
    "MNNStrategyLearningCycle",
    "MNNStrategyOutcomeJournal",
    "MNNStrategyEventBridge",
    "MNNEventMemoryProjector",
    "MNNEventProjectionResult",
    "MNNAutobiographicalEpisode",
    "MNNAutobiographicalRecall",
    "MNNAutobiographicalStrategyAdvisor",
    "StrategyFeedback",
    "StrategyLearningResult",
    "MNNSynapticConsolidator",
    "MNNShortTermPlasticity",
    "MNNPlasticityController",
    "MNNPlasticityProposal",
    "MNNExperiencePlasticityAdvisor",
    "MNNExperiencePlasticityProposal",
    "MNNExperienceCycle",
    "AutobiographicalLearningSignal",
    "MNNAutobiographicalLearningAdvisor",
    "MNNAutobiographicalConsolidationAdapter",
]
