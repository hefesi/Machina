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

    def update_prediction_calibration(
        self,
        property_name: str,
        *,
        cycle_id: str,
        horizon: str | None = None,
        capability_name: str | None = None,
        min_evaluated: int = 5,
        minimum_coverage: float = 0.5,
    ) -> dict[str, Any]:
        """Project sufficiently sampled self-prediction history into an inferred capability."""
        if isinstance(min_evaluated, bool) or not isinstance(min_evaluated, int) or min_evaluated < 1:
            raise ValueError("min_evaluated must be a positive integer")
        try:
            coverage_floor = float(minimum_coverage)
        except (TypeError, ValueError) as exc:
            raise ValueError("minimum_coverage must be finite and in [0, 1]") from exc
        if not 0.0 <= coverage_floor <= 1.0:
            raise ValueError("minimum_coverage must be finite and in [0, 1]")
        report = self.self_model.calibration_report(property_name=property_name, horizon=horizon)
        metrics = report["overall"]
        if metrics["evaluated"] < min_evaluated:
            raise ValueError(f"insufficient evaluated predictions: {metrics['evaluated']} < {min_evaluated}")
        if metrics["coverage"] is None or metrics["coverage"] < coverage_floor:
            raise ValueError("prediction evaluation coverage is below minimum_coverage")
        history = self.self_model.prediction_history
        horizon_by_ref = {item["prediction_ref"]: item["horizon"] for item in history["predictions"]}
        evidence_refs = sorted(
            item["evidence_ref"] for item in history["evaluations"]
            if item["property"] == property_name
            and (horizon is None or horizon_by_ref.get(item["prediction_ref"]) == horizon)
        )
        name = capability_name or property_name
        evidence_ref = "prediction-calibration:" + "|".join(evidence_refs)
        evidence_confidence = min(1.0, metrics["evaluated"] / min_evaluated) * metrics["coverage"]
        estimate = {
            "kind": "empirical_self_prediction_calibration",
            "property": property_name, "horizon": horizon,
            "accuracy": metrics["accuracy"],
            "mean_declared_confidence": metrics["mean_confidence"],
            "calibration_gap": metrics["calibration_gap"],
            "evaluated": metrics["evaluated"], "emitted": metrics["emitted"],
            "pending": metrics["pending"], "coverage": metrics["coverage"],
            "evidence_sufficiency": evidence_confidence,
        }
        state = self.self_model.update(
            {}, cycle_id=cycle_id,
            capability_estimates={name: {
                "estimate": estimate, "confidence": evidence_confidence,
                "status": "inferred", "evidence_ref": evidence_ref,
            }},
        )
        return {
            "self_model": state, "capability_name": name, "estimate": estimate,
            "evidence_ref": evidence_ref, "status": "inferred",
        }

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
