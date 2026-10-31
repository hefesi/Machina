"""Evidence-gated plasticity proposals from autobiographical strategy outcomes.

The adapter requires an explicit action-to-connection map supplied by the
integrator. It never infers which synapses caused an outcome and never applies
weights during review.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from types import MappingProxyType
from typing import Any, Mapping

from .mnn import MNN
from .mnn_autobiographical_strategy_advisor import MNNAutobiographicalStrategyAdvisor
from .mnn_plasticity_control import MNNPlasticityController, MNNPlasticityProposal


@dataclass(frozen=True, slots=True)
class MNNExperiencePlasticityProposal:
    """A plasticity candidate tied to confirmed autobiographical evidence."""

    proposal_id: str
    context: str
    action: str
    mean_observed_reward: float
    evidence_event_ids: tuple[str, ...]
    cycle_ids: tuple[str, ...]
    connection_ids: tuple[str, ...]
    strategy_review: Mapping[str, Any]
    plasticity: MNNPlasticityProposal


class MNNExperiencePlasticityAdvisor:
    """Translate repeated strategy evidence into inspectable, unapplied proposals.

    The action-to-connection mapping is explicit configuration. It is a
    hypothesis supplied by the caller, not a learned causal attribution.
    """

    def __init__(
        self,
        strategy_advisor: MNNAutobiographicalStrategyAdvisor,
        controller: MNNPlasticityController,
        network: MNN,
        action_connection_map: Mapping[str, tuple[str, ...] | list[str]],
    ) -> None:
        if not isinstance(strategy_advisor, MNNAutobiographicalStrategyAdvisor):
            raise TypeError("strategy_advisor must be an MNNAutobiographicalStrategyAdvisor")
        if not isinstance(controller, MNNPlasticityController):
            raise TypeError("controller must be an MNNPlasticityController")
        if not isinstance(network, MNN):
            raise TypeError("network must be an MNN")
        if not isinstance(action_connection_map, Mapping) or not action_connection_map:
            raise ValueError("action_connection_map must be a non-empty mapping")
        normalized: dict[str, tuple[str, ...]] = {}
        for action, connection_ids in action_connection_map.items():
            if not isinstance(action, str) or not action.strip():
                raise ValueError("mapped action names must be non-empty strings")
            if action not in strategy_advisor.actions:
                raise ValueError(f"mapped action is not configured in strategy advisor: {action}")
            if isinstance(connection_ids, (str, bytes)) or not isinstance(connection_ids, (tuple, list)):
                raise ValueError("connection IDs must be supplied as a list or tuple")
            ids = tuple(connection_ids)
            if not ids or len(set(ids)) != len(ids):
                raise ValueError("each action must map to unique, non-empty connection IDs")
            if any(not isinstance(item, str) or item not in network.connections for item in ids):
                raise ValueError("every mapped connection ID must exist in the network")
            normalized[action.strip()] = ids
        self.strategy_advisor = strategy_advisor
        self.controller = controller
        self.network = network
        self.action_connection_map = MappingProxyType(normalized)

    def review_and_propose(
        self,
        context: str,
        *,
        current_action: str,
        proposal_id: str,
        learning_rate: float,
        max_delta: float = 0.02,
    ) -> MNNExperiencePlasticityProposal | None:
        """Return None on abstention; otherwise prepare but do not apply weights."""
        if not isinstance(proposal_id, str) or not proposal_id.strip():
            raise ValueError("proposal_id must be non-empty")
        review = self.strategy_advisor.review(context, current_action=current_action)
        if review.get("status") != "candidate":
            return None
        action = review.get("candidate_action")
        if not isinstance(action, str) or action not in self.action_connection_map:
            return None
        summaries = review.get("action_summaries")
        summary = summaries.get(action) if isinstance(summaries, Mapping) else None
        if not isinstance(summary, Mapping):
            return None
        reward = summary.get("mean_observed_reward")
        if (isinstance(reward, bool) or not isinstance(reward, (int, float))
                or not math.isfinite(reward) or not 0.0 <= reward <= 1.0):
            return None
        event_ids = summary.get("event_ids")
        cycle_ids = summary.get("cycle_ids")
        if (not isinstance(event_ids, list) or not event_ids
                or any(not isinstance(item, str) or not item for item in event_ids)):
            return None
        if (not isinstance(cycle_ids, list) or not cycle_ids
                or any(not isinstance(item, str) or not item for item in cycle_ids)):
            return None
        ids = self.action_connection_map[action]
        plasticity = self.controller.propose_hebbian(
            self.network,
            proposal_id=proposal_id,
            learning_rate=learning_rate,
            reward=float(reward),
            max_delta=max_delta,
            connection_ids=ids,
        )
        return MNNExperiencePlasticityProposal(
            proposal_id=proposal_id,
            context=" ".join(context.casefold().split()),
            action=action,
            mean_observed_reward=float(reward),
            evidence_event_ids=tuple(event_ids),
            cycle_ids=tuple(cycle_ids),
            connection_ids=ids,
            strategy_review=MappingProxyType(dict(review)),
            plasticity=plasticity,
        )

    def apply(self, proposal: MNNExperiencePlasticityProposal) -> dict[str, float]:
        """Apply a previously reviewed proposal only on explicit caller request."""
        if not isinstance(proposal, MNNExperiencePlasticityProposal):
            raise TypeError("proposal must be an MNNExperiencePlasticityProposal")
        if proposal.connection_ids != self.action_connection_map.get(proposal.action):
            raise ValueError("proposal action-to-connection mapping is no longer configured")
        return self.controller.apply(self.network, proposal.plasticity)

    def rollback(self, proposal: MNNExperiencePlasticityProposal) -> dict[str, float]:
        """Conditionally undo an applied proposal without overwriting later edits."""
        if not isinstance(proposal, MNNExperiencePlasticityProposal):
            raise TypeError("proposal must be an MNNExperiencePlasticityProposal")
        return self.controller.rollback(self.network, proposal.proposal_id)
