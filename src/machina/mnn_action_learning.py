"""A bounded MNN-backed action-value learner for small controlled experiments.

Each candidate action is represented by one connection weight in the MNN.
Weights are predicted utility; observed rewards update the selected edge using
a prediction error. This is a compact contextual-free bandit baseline.
"""
from __future__ import annotations

import math
import random
from typing import Mapping

from .mnn import Connection, MNN, Unit


class MNNActionLearner:
    """Select actions, predict reward, learn from outcomes, and persist state.

    The first pass explores each action once. Later, every exploration_interval
    decisions force a rotating exploratory action; otherwise the highest
    predicted-value action is selected. This deterministic policy is reproducible
    and supports measuring adaptation after reward distributions change.
    """

    def __init__(
        self,
        actions: list[str] | tuple[str, ...],
        *,
        network: MNN | None = None,
        learning_rate: float = 0.2,
        exploration_interval: int = 5,
        exploration_seed: int = 0,
    ) -> None:
        names = tuple(actions)
        if len(names) < 2 or any(not isinstance(name, str) or not name for name in names):
            raise ValueError("at least two non-empty action names are required")
        if len(set(names)) != len(names):
            raise ValueError("action names must be unique")
        self.actions = names
        self.learning_rate = float(learning_rate)
        if not math.isfinite(self.learning_rate) or not 0.0 < self.learning_rate <= 1.0:
            raise ValueError("learning_rate must be finite and in (0, 1]")
        if isinstance(exploration_interval, bool) or not isinstance(exploration_interval, int) or exploration_interval < 1:
            raise ValueError("exploration_interval must be a positive integer")
        self.exploration_interval = exploration_interval
        if isinstance(exploration_seed, bool) or not isinstance(exploration_seed, int):
            raise ValueError("exploration_seed must be an integer")
        self.exploration_seed = exploration_seed
        self.network = network or self._new_network(names)
        self._action_edges = {name: f"action-value:{name}" for name in names}
        missing = set(self._action_edges.values()) - set(self.network.connections)
        if missing:
            raise ValueError(f"network is missing action-value edges: {sorted(missing)}")
        self.counts = {name: 0 for name in names}
        self.decisions = 0
        self._last_action: str | None = None
        self.last_selection_mode: str | None = None

    @staticmethod
    def _new_network(actions: tuple[str, ...]) -> MNN:
        network = MNN(weight_limit=5.0)
        network.add_unit(Unit("context", state=1.0, activation="identity"))
        for action in actions:
            network.add_unit(Unit(f"value:{action}", activation="identity"))
            network.add_connection(Connection(
                f"action-value:{action}", "context", f"value:{action}", 0.0
            ))
        return network

    def predictions(self) -> dict[str, float]:
        """Return the learned expected utility for each action."""
        return {
            action: self.network.connections[self._action_edges[action]].weight
            for action in self.actions
        }

    def choose(self, *, epsilon: float | None = None) -> str:
        """Choose using the original schedule or reproducible epsilon-greedy.

        When epsilon is omitted, preserve the original deterministic schedule.
        When supplied, epsilon must be in [0, 1]; unseen actions are tried first,
        then a seeded pseudo-random draw explores with probability epsilon.
        Deriving the draw from seed + decision number keeps restarts reproducible.
        """
        if epsilon is not None and (
            isinstance(epsilon, bool)
            or not isinstance(epsilon, (int, float))
            or not math.isfinite(epsilon)
            or not 0.0 <= epsilon <= 1.0
        ):
            raise ValueError("epsilon must be a finite number in [0, 1]")
        self.decisions += 1
        unexplored = [name for name in self.actions if self.counts[name] == 0]
        if unexplored:
            action = unexplored[0]
            self.last_selection_mode = "initial_coverage"
        elif epsilon is not None:
            rng = random.Random(self.exploration_seed + self.decisions)
            if rng.random() < float(epsilon):
                action = rng.choice(self.actions)
                self.last_selection_mode = "epsilon_explore"
            else:
                predictions = self.predictions()
                action = max(self.actions, key=lambda name: (predictions[name], -self.actions.index(name)))
                self.last_selection_mode = "greedy"
        elif self.decisions % self.exploration_interval == 0:
            action = self.actions[(self.decisions // self.exploration_interval) % len(self.actions)]
            self.last_selection_mode = "scheduled_exploration"
        else:
            predictions = self.predictions()
            action = max(self.actions, key=lambda name: (predictions[name], -self.actions.index(name)))
            self.last_selection_mode = "greedy"
        self._last_action = action
        return action

    def observe(self, reward: float, *, action: str | None = None) -> dict:
        """Update the selected action's predicted utility from its observed reward."""
        value = float(reward)
        if not math.isfinite(value):
            raise ValueError("reward must be finite")
        selected = action or self._last_action
        if selected not in self._action_edges:
            raise ValueError("observe requires a known action selected by choose or passed explicitly")
        edge = self.network.connections[self._action_edges[selected]]
        prediction = edge.weight
        error = value - prediction
        delta = self.learning_rate * error
        updated = max(-self.network.weight_limit, min(self.network.weight_limit, prediction + delta))
        edge.weight = updated
        self.counts[selected] += 1
        self._last_action = None
        return {
            "action": selected,
            "prediction_before": prediction,
            "reward": value,
            "prediction_error": error,
            "weight_change": updated - prediction,
            "prediction_after": updated,
            "observations": self.counts[selected],
        }

    def snapshot(self) -> dict:
        """Return JSON-compatible learner state for durable restart."""
        return {
            "schema_version": 1,
            "actions": list(self.actions),
            "learning_rate": self.learning_rate,
            "exploration_interval": self.exploration_interval,
            "exploration_seed": self.exploration_seed,
            "decisions": self.decisions,
            "counts": dict(self.counts),
            "last_action": self._last_action,
            "last_selection_mode": self.last_selection_mode,
            "network": self.network.snapshot(),
        }

    @classmethod
    def from_snapshot(cls, data: Mapping) -> "MNNActionLearner":
        if data.get("schema_version") != 1:
            raise ValueError("unsupported MNN action-learner snapshot schema")
        learner = cls(
            data["actions"],
            network=MNN.from_snapshot(data["network"]),
            learning_rate=data["learning_rate"],
            exploration_interval=data["exploration_interval"],
            exploration_seed=data.get("exploration_seed", 0),
        )
        counts = data["counts"]
        if set(counts) != set(learner.actions):
            raise ValueError("snapshot counts must match the configured actions")
        normalized = {}
        for action, count in counts.items():
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise ValueError(f"count for {action!r} must be a non-negative integer")
            normalized[action] = count
        decisions = data["decisions"]
        if isinstance(decisions, bool) or not isinstance(decisions, int) or decisions < 0:
            raise ValueError("decisions must be a non-negative integer")
        last_action = data.get("last_action")
        if last_action is not None and last_action not in learner.actions:
            raise ValueError("last_action is not a configured action")
        learner.counts = normalized
        learner.decisions = decisions
        learner._last_action = last_action
        selection_mode = data.get("last_selection_mode")
        if selection_mode not in (None, "initial_coverage", "epsilon_explore", "greedy", "scheduled_exploration"):
            raise ValueError("invalid last_selection_mode in snapshot")
        learner.last_selection_mode = selection_mode
        return learner
