"""A minimal action -> outcome -> persistent experience loop for Machina.

The agent coordinates a bounded action-value learner with FragmentMemory.
Memory is an auditable record of outcomes; it is not treated as semantic
understanding and does not silently rewrite the policy.
"""
from __future__ import annotations

import math
import re
from typing import Iterable, Mapping

from .fragment_memory import FragmentMemory, MemoryFragment
from .mnn_action_learning import MNNActionLearner
from .mnn_concept_advisor import MNNConceptAdvisor
from .mnn_contextual_outcome_policy import MNNContextualOutcomePolicy
from .mnn_reward_drift import MNNRewardDriftDetector
from .mnn_strategy_review import MNNStrategyReviewer
from .mnn_strategy_experiment import MNNStrategyExperimentLog


class MNNLearningAgent:
    """Coordinate one pending action, outcome-based learning, and memory."""

    def __init__(
        self,
        learner: MNNActionLearner,
        memory: FragmentMemory,
        *,
        agent_id: str = "machina",
        concept_advisor: MNNConceptAdvisor | None = None,
        outcome_policy: MNNContextualOutcomePolicy | None = None,
        reward_drift_detector: MNNRewardDriftDetector | None = None,
        strategy_reviewer: MNNStrategyReviewer | None = None,
        strategy_experiment_log: MNNStrategyExperimentLog | None = None,
    ) -> None:
        if not isinstance(agent_id, str) or not agent_id.strip():
            raise ValueError("agent_id must be a non-empty string")
        self.learner = learner
        self.memory = memory
        self.agent_id = agent_id.strip()
        if concept_advisor is not None and not isinstance(concept_advisor, MNNConceptAdvisor):
            raise ValueError("concept_advisor must be an MNNConceptAdvisor or None")
        self.concept_advisor = concept_advisor
        if outcome_policy is not None and not isinstance(outcome_policy, MNNContextualOutcomePolicy):
            raise ValueError("outcome_policy must be an MNNContextualOutcomePolicy or None")
        if outcome_policy is not None and tuple(outcome_policy.actions) != tuple(learner.actions):
            raise ValueError("outcome_policy actions must match learner actions in the same order")
        self.outcome_policy = outcome_policy
        if reward_drift_detector is not None and not isinstance(
            reward_drift_detector, MNNRewardDriftDetector
        ):
            raise ValueError("reward_drift_detector must be an MNNRewardDriftDetector or None")
        if reward_drift_detector is not None and reward_drift_detector.memory is not memory:
            raise ValueError("reward_drift_detector must use the agent's memory instance")
        self.reward_drift_detector = reward_drift_detector
        if strategy_reviewer is not None and not isinstance(strategy_reviewer, MNNStrategyReviewer):
            raise ValueError("strategy_reviewer must be an MNNStrategyReviewer or None")
        if strategy_reviewer is not None and strategy_reviewer.detector.memory is not memory:
            raise ValueError("strategy_reviewer must use the agent's memory instance")
        if strategy_reviewer is not None and tuple(strategy_reviewer.actions) != tuple(learner.actions):
            raise ValueError("strategy_reviewer actions must match learner actions in the same order")
        self.strategy_reviewer = strategy_reviewer
        if strategy_experiment_log is not None and not isinstance(
            strategy_experiment_log, MNNStrategyExperimentLog
        ):
            raise ValueError("strategy_experiment_log must be an MNNStrategyExperimentLog or None")
        if strategy_experiment_log is not None and strategy_experiment_log.memory is not memory:
            raise ValueError("strategy_experiment_log must use the agent's memory instance")
        if strategy_experiment_log is not None and tuple(strategy_experiment_log.actions) != tuple(learner.actions):
            raise ValueError("strategy_experiment_log actions must match learner actions in the same order")
        self.strategy_experiment_log = strategy_experiment_log
        self.pending_action: str | None = None
        self.pending_action_source: str | None = None
        self.experience_count = 0

    def decide(
        self, *, context: str | None = None, use_memory: bool = False,
        exploration_epsilon: float | None = None,
        use_concepts: bool = False,
        context_tags: Iterable[str] | None = None,
        use_outcome_policy: bool = False,
        review_reward_drift: bool = False,
        review_strategy: bool = False,
    ) -> dict:
        """Choose an action, optionally using an explicit contextual memory recommendation.

        The learner always advances its decision counter and provides a fallback.
        When use_memory=True, a usable memory recommendation overrides that
        fallback for this decision only; learning still occurs in resolve().
        """
        if self.pending_action is not None:
            raise RuntimeError("resolve the pending action before choosing another")
        if not isinstance(use_memory, bool):
            raise ValueError("use_memory must be boolean")
        if not isinstance(use_concepts, bool):
            raise ValueError("use_concepts must be boolean")
        if not isinstance(use_outcome_policy, bool):
            raise ValueError("use_outcome_policy must be boolean")
        if not isinstance(review_reward_drift, bool):
            raise ValueError("review_reward_drift must be boolean")
        if not isinstance(review_strategy, bool):
            raise ValueError("review_strategy must be boolean")
        if review_strategy and self.strategy_reviewer is None:
            raise ValueError("review_strategy=True requires a configured strategy_reviewer")
        if review_strategy and (context is None or not context.strip()):
            raise ValueError("a non-empty context is required when review_strategy=True")
        if review_reward_drift and self.reward_drift_detector is None:
            raise ValueError("review_reward_drift=True requires a configured reward_drift_detector")
        if review_reward_drift and (context is None or not context.strip()):
            raise ValueError("a non-empty context is required when review_reward_drift=True")
        if use_outcome_policy and self.outcome_policy is None:
            raise ValueError("use_outcome_policy=True requires a configured outcome_policy")
        if use_outcome_policy and (context is None or not context.strip()):
            raise ValueError("a non-empty context is required when use_outcome_policy=True")
        if use_concepts and self.concept_advisor is None:
            raise ValueError("use_concepts=True requires a configured concept_advisor")
        if use_concepts and context_tags is None:
            raise ValueError("context_tags are required when use_concepts=True")
        if context_tags is not None and not use_concepts:
            raise ValueError("context_tags require use_concepts=True")
        if context is not None and not isinstance(context, str):
            raise ValueError("context must be a string")
        if use_memory and (context is None or not context.strip()):
            raise ValueError("a non-empty context is required when use_memory=True")

        # Validate and gather optional recommendations before advancing the learner's
        # decision counter, so invalid context input cannot partially mutate state.
        concept_result = (
            self.concept_advisor.recommend(context_tags)
            if use_concepts and self.concept_advisor is not None and context_tags is not None
            else None
        )
        concept_recommendation = (
            concept_result["recommendation"]
            if concept_result is not None and concept_result["status"] == "recommended"
            else None
        )
        drift_result = (
            self.reward_drift_detector.detect(context)
            if review_reward_drift and self.reward_drift_detector is not None and context is not None
            else None
        )
        outcome_result = (
            self.outcome_policy.recommend(context)
            if use_outcome_policy and self.outcome_policy is not None and context is not None
            else None
        )
        outcome_recommendation = (
            outcome_result if outcome_result is not None and outcome_result.get("status") == "recommended"
            else None
        )
        recommendation = (
            self.recommend_from_memory(context)
            if use_memory and context is not None
            else None
        )
        fallback = self.learner.choose(epsilon=exploration_epsilon)
        if concept_recommendation is not None:
            action = concept_recommendation["action"]
            source = "concept"
        elif outcome_recommendation is not None:
            action = outcome_recommendation["action"]
            source = "outcome_policy"
        elif recommendation is not None:
            action = recommendation["action"]
            source = "memory"
        else:
            action = fallback
            source = "learner"
        strategy_result = (
            self.strategy_reviewer.review(context, current_action=action)
            if review_strategy and self.strategy_reviewer is not None and context is not None
            else None
        )
        self.pending_action = action
        self.pending_action_source = source
        return {
            "action": action,
            "predicted_utility": self.learner.predictions()[action],
            "decision": self.learner.decisions,
            "context": context,
            "selection_source": source,
            "memory_recommendation": recommendation,
            "concept_guidance": concept_result,
            "outcome_policy_result": outcome_result,
            "reward_drift_review": drift_result,
            "strategy_review": strategy_result,
            "fallback_action": fallback,
            "exploration_policy": "epsilon_greedy" if exploration_epsilon is not None else "scheduled",
            "exploration_epsilon": exploration_epsilon,
            "memory_status": (
                "recommended" if recommendation
                else "no_recommendation" if use_memory
                else "not_consulted"
            ),
            "fallback_reason": (
                "no_matching_or_unambiguous_memory_evidence"
                if use_memory and recommendation is None
                else None
            ),
            # Signals that the environment should gather another observed outcome;
            # this does not fabricate or automatically execute a trial.
            "request_experience": bool(
                (use_memory and recommendation is None and concept_recommendation is None and outcome_recommendation is None)
                or (use_concepts and concept_recommendation is None)
                or (use_outcome_policy and outcome_recommendation is None)
                or (review_reward_drift and drift_result is not None and drift_result["status"] in {"detected", "abstain"})
                or (review_strategy and strategy_result is not None and strategy_result["status"] in {"candidate", "abstain"})
            ),
        }

    def record_strategy_experiment_proposal(
        self, experiment_id: str, decision: Mapping, *, hypothesis: str,
        planned_action: str | None = None,
    ) -> MemoryFragment:
        """Explicitly persist a reviewed proposal; never executes the planned action."""
        if self.strategy_experiment_log is None:
            raise ValueError("a strategy_experiment_log must be configured")
        if not isinstance(decision, Mapping):
            raise ValueError("decision must be the mapping returned by decide()")
        context = decision.get("context")
        current_action = decision.get("action")
        review = decision.get("strategy_review")
        if not isinstance(context, str) or not context.strip():
            raise ValueError("decision must include a non-empty context")
        if not isinstance(current_action, str) or current_action not in self.learner.actions:
            raise ValueError("decision must include a configured current action")
        if not isinstance(review, Mapping):
            raise ValueError("decision must include strategy_review from review_strategy=True")
        candidate = review.get("candidate_action")
        selected_plan = planned_action if planned_action is not None else candidate
        if selected_plan is None:
            raise ValueError("planned_action is required when the review has no candidate")
        return self.strategy_experiment_log.begin(
            experiment_id, hypothesis=hypothesis, context=context,
            current_action=current_action, planned_action=selected_plan, review=review,
        )

    def record_strategy_experiment_outcome(
        self, experiment_id: str, *, tested_action: str, observed_reward: float,
        decision: str, observation: str = "",
    ) -> MemoryFragment:
        """Persist an externally observed trial result; does not change the policy."""
        if self.strategy_experiment_log is None:
            raise ValueError("a strategy_experiment_log must be configured")
        return self.strategy_experiment_log.complete(
            experiment_id, tested_action=tested_action, observed_reward=observed_reward,
            decision=decision, observation=observation,
        )

    def resolve(self, reward: float, *, context: str = "") -> dict:
        """Learn from the pending action and archive its observed outcome."""
        if self.pending_action is None:
            raise RuntimeError("cannot resolve an outcome without a pending action")
        if isinstance(reward, bool):
            raise ValueError("reward must be a finite number")
        try:
            value = float(reward)
        except (TypeError, ValueError) as error:
            raise ValueError("reward must be a finite number") from error
        if not math.isfinite(value):
            raise ValueError("reward must be a finite number")
        if not isinstance(context, str):
            raise ValueError("context must be a string")

        action = self.pending_action
        update = self.learner.observe(value, action=action)
        fragment = self.memory.add(
            f"Action '{action}' received reward {value:g}."
            + (f" Context: {context.strip()}" if context.strip() else ""),
            kind="action-outcome",
            source_uri=f"machina://{self.agent_id}/experience/{self.experience_count + 1}",
            importance=min(1.0, 0.5 + abs(value) / 10.0),
            confidence=1.0,
            tags=("action-learning", action, "positive-outcome" if value > 0 else "non-positive-outcome"),
            metadata={
                "agent_id": self.agent_id,
                "action": action,
                "reward": value,
                "prediction_error": update["prediction_error"],
                "decision": self.learner.decisions,
                "context": context.strip(),
            },
        )
        self.experience_count += 1
        self.pending_action = None
        self.pending_action_source = None
        return {
            "learning_update": update,
            "experience_id": fragment.id,
            "experience_count": self.experience_count,
            "predictions": self.learner.predictions(),
        }

    def recall(self, query: str, *, limit: int = 5) -> list[MemoryFragment]:
        """Recall explicit experience records using FragmentMemory's lexical search."""
        return self.memory.recall(query, limit=limit)

    def recommend_from_memory(
        self, context: str, *, limit: int = 20, min_reward_margin: float = 0.1
    ) -> dict | None:
        """Recommend an action from context-matching archived outcomes.

        This is an explicit, explainable memory-based recommendation; it does
        not modify the learner or choose an action automatically. Only recorded
        action-outcome fragments with a known action and overlapping context
        tokens participate. Rewards are averaged per action, weighted by
        context-token overlap. Returns None when no usable context evidence
        exists, so callers can fall back to the ordinary learner.
        """
        if not isinstance(context, str) or not context.strip():
            raise ValueError("context must be a non-empty string")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        if (
            isinstance(min_reward_margin, bool)
            or not isinstance(min_reward_margin, (int, float))
            or not math.isfinite(min_reward_margin)
            or min_reward_margin < 0
        ):
            raise ValueError("min_reward_margin must be a finite non-negative number")

        def tokens(value: str) -> set[str]:
            return {
                token.casefold()
                for token in re.findall(r"\w+", value, flags=re.UNICODE)
                if len(token) > 1
            }

        query_tokens = tokens(context)
        if not query_tokens:
            return None
        fragments = self.memory.recall(context, limit=limit)
        totals: dict[str, float] = {}
        weights: dict[str, float] = {}
        evidence: dict[str, list[str]] = {}
        for fragment in fragments:
            if fragment.kind != "action-outcome":
                continue
            metadata = fragment.metadata
            action = metadata.get("action")
            stored_context = metadata.get("context", "")
            if action not in self.learner.actions or not isinstance(stored_context, str):
                continue
            overlap = len(query_tokens & tokens(stored_context)) / len(query_tokens)
            if overlap <= 0:
                continue
            reward = metadata.get("reward")
            if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
                continue
            weight = overlap * max(0.01, fragment.confidence)
            totals[action] = totals.get(action, 0.0) + float(reward) * weight
            weights[action] = weights.get(action, 0.0) + weight
            evidence.setdefault(action, []).append(fragment.id)

        if not weights:
            return None
        estimates = {action: totals[action] / weights[action] for action in weights}
        ranked_actions = sorted(
            estimates,
            key=lambda name: (-estimates[name], self.learner.actions.index(name)),
        )
        # If the best two observed actions are too close, abstain instead of
        # letting configured action order turn ambiguous evidence into certainty.
        if (
            len(ranked_actions) > 1
            and estimates[ranked_actions[0]] - estimates[ranked_actions[1]]
            < float(min_reward_margin)
        ):
            return None
        action = ranked_actions[0]
        return {
            "action": action,
            "estimated_reward": estimates[action],
            "context": context.strip(),
            "evidence_ids": evidence[action],
            "evidence_counts": {name: len(ids) for name, ids in evidence.items()},
            "estimates_by_action": estimates,
            "decision_margin": (
                estimates[ranked_actions[0]] - estimates[ranked_actions[1]]
                if len(ranked_actions) > 1 else None
            ),
            "min_reward_margin": float(min_reward_margin),
            "method": "lexical-context-overlap-weighted-reward-mean-with-abstention",
        }

    def snapshot(self) -> dict:
        """Capture learner and in-flight action state; SQLite is persisted separately."""
        return {
            "schema_version": 2,
            "agent_id": self.agent_id,
            "learner": self.learner.snapshot(),
            "pending_action": self.pending_action,
            "pending_action_source": self.pending_action_source,
            "experience_count": self.experience_count,
        }

    @classmethod
    def from_snapshot(
        cls, data: Mapping, memory: FragmentMemory, *,
        concept_advisor: MNNConceptAdvisor | None = None,
        outcome_policy: MNNContextualOutcomePolicy | None = None,
        strategy_experiment_log: MNNStrategyExperimentLog | None = None,
    ) -> "MNNLearningAgent":
        schema_version = data.get("schema_version")
        if schema_version not in (1, 2):
            raise ValueError("unsupported MNN learning-agent snapshot schema")
        learner = MNNActionLearner.from_snapshot(data["learner"])
        agent = cls(
            learner, memory, agent_id=data["agent_id"],
            concept_advisor=concept_advisor, outcome_policy=outcome_policy,
            strategy_experiment_log=strategy_experiment_log,
        )
        pending = data.get("pending_action")
        if pending is not None and pending not in learner.actions:
            raise ValueError("pending_action is not a configured action")
        count = data.get("experience_count")
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ValueError("experience_count must be a non-negative integer")

        # Schema v1 only represented learner-selected pending actions. Schema v2
        # records whether contextual memory overrode the learner's fallback.
        source = data.get("pending_action_source", "learner" if pending is not None else None)
        if source not in (None, "learner", "memory", "concept", "outcome_policy"):
            raise ValueError("pending_action_source must be 'learner', 'memory', 'concept', 'outcome_policy', or None")
        if (pending is None) != (source is None):
            raise ValueError("pending_action and pending_action_source must both be set or unset")
        if pending is not None and source == "learner" and learner._last_action != pending:
            raise ValueError("pending_action does not match the learner's pending choice")
        if pending is not None and source in ("memory", "concept", "outcome_policy") and learner._last_action not in learner.actions:
            raise ValueError(f"{source}-selected pending action requires a valid learner fallback")

        agent.pending_action = pending
        agent.pending_action_source = source
        agent.experience_count = count
        return agent
