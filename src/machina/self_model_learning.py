"""Bridge empirical outcome learning into Machina's operational self-model."""
from __future__ import annotations

from typing import Any

from .goal_outcome_learning import GoalOutcomeLearner
from .self_model import SelfModel


class SelfModelLearningBridge:
    """Translate evaluator-backed outcome history into cautious self-beliefs.

    Estimates are marked inferred, not observed: they summarize past outcomes
    and do not prove an intrinsic or universal capability.
    """

    def __init__(self, self_model: SelfModel, learner: GoalOutcomeLearner) -> None:
        if not isinstance(self_model, SelfModel):
            raise TypeError("self_model must be a SelfModel")
        if not isinstance(learner, GoalOutcomeLearner):
            raise TypeError("learner must be a GoalOutcomeLearner")
        self.self_model = self_model
        self.learner = learner

    def update_capability(
        self,
        goal_type: str,
        *,
        capability_name: str | None = None,
        cycle_id: str,
    ) -> dict[str, Any]:
        prediction = self.learner.predict(goal_type)
        history = self.learner.history(goal_type, limit=1)
        if not history:
            raise ValueError("cannot update self-model without evaluated outcome history")
        latest = history[0]
        name = capability_name or goal_type
        confidence = max(0.0, min(1.0, 1.0 - float(prediction["uncertainty"]) * 2.0))
        evidence_ref = f"goal-outcome:{latest['id']}"
        state = self.self_model.update(
            {},
            cycle_id=cycle_id,
            capability_estimates={
                name: {
                    "estimate": {
                        "predicted_outcome": prediction["predicted_outcome"],
                        "uncertainty": prediction["uncertainty"],
                        "observations": prediction["observations"],
                    },
                    "confidence": confidence,
                    "status": "inferred",
                    "evidence_ref": evidence_ref,
                }
            },
        )
        self.self_model.record_prediction_error({
            "prediction_ref": evidence_ref,
            "goal_type": goal_type,
            "error": latest["prediction_error"],
            "squared_error": float(latest["prediction_error"]) ** 2,
            "observed_outcome": latest["outcome"],
            "prediction_before": latest["prediction_before"],
        })
        return {
            "self_model": state,
            "capability_name": name,
            "estimate": prediction,
            "evidence_ref": evidence_ref,
            "status": "inferred",
        }
