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


    def propose_goals_from_limitations(
        self,
        goal_mappings: Mapping[str, Mapping[str, Any]],
        *,
        allow_inferred: bool = False,
        minimum_confidence: float = 0.7,
    ) -> dict[str, Any]:
        """Create internal goal candidates from evidence-backed self-limitations.

        Mapping keys must match known_limitations. Each mapping supplies a
        description and drive. Observed beliefs are accepted by default;
        inferred beliefs require explicit opt-in, a confidence threshold,
        and an evidence reference. Unknown and stale beliefs are ignored.
        """
        import re
        from .autonomy import GoalCandidate

        if not isinstance(goal_mappings, Mapping):
            raise ValueError("goal_mappings must be a mapping")
        if not isinstance(allow_inferred, bool):
            raise ValueError("allow_inferred must be a boolean")
        if isinstance(minimum_confidence, bool):
            raise ValueError("minimum_confidence must be finite and in [0, 1]")
        try:
            floor = float(minimum_confidence)
        except (TypeError, ValueError) as exc:
            raise ValueError("minimum_confidence must be finite and in [0, 1]") from exc
        if not 0.0 <= floor <= 1.0:
            raise ValueError("minimum_confidence must be finite and in [0, 1]")

        limitations = set(self.self_model.known_limitations)
        beliefs = self.self_model.beliefs
        goals, provenance, seen = [], [], set()
        for raw_limitation, spec in goal_mappings.items():
            if not isinstance(raw_limitation, str) or not raw_limitation.strip():
                raise ValueError("limitation mapping keys must be non-empty strings")
            limitation = raw_limitation.strip()
            if limitation not in limitations:
                continue
            if not isinstance(spec, Mapping):
                raise ValueError("each goal mapping must be a mapping")
            prop = spec.get("belief_property", limitation)
            if not isinstance(prop, str) or not prop.strip():
                raise ValueError("belief_property must be a non-empty string")
            belief = beliefs.get(prop.strip())
            if belief is None:
                continue
            status = belief.get("status")
            evidence = belief.get("evidence_ref")
            confidence = float(belief.get("confidence", 0.0))
            if status == "observed":
                if not isinstance(evidence, str) or not evidence.strip():
                    continue
            elif status == "inferred":
                if not allow_inferred or confidence < floor:
                    continue
                if not isinstance(evidence, str) or not evidence.strip():
                    continue
            else:
                continue

            description, drive = spec.get("description"), spec.get("drive")
            if not isinstance(description, str) or not description.strip():
                raise ValueError("goal mapping requires a non-empty description")
            if not isinstance(drive, str) or not drive.strip():
                raise ValueError("goal mapping requires a non-empty drive")
            slug = re.sub(r"[^a-z0-9]+", "-", limitation.lower()).strip("-") or "limitation"
            goal_id = "address_limitation:" + slug
            if goal_id in seen:
                raise ValueError("duplicate generated goal_id: " + goal_id)
            goal = GoalCandidate(
                goal_id=goal_id,
                description=description.strip(),
                drive=drive.strip(),
                urgency=spec.get("urgency", 0.65),
                expected_benefit=spec.get("expected_benefit", 0.65),
                confidence=min(0.8, confidence),
                estimated_cost=spec.get("estimated_cost", 0.25),
                risk=spec.get("risk", 0.05),
                requires_external_action=False,
            )
            seen.add(goal_id)
            goals.append(goal)
            provenance.append({
                "goal_id": goal_id,
                "limitation": limitation,
                "belief_property": prop.strip(),
                "source_status": status,
                "source_confidence": confidence,
                "evidence_ref": evidence,
                "observed_at_cycle": belief.get("observed_at_cycle"),
            })
        return {"goals": goals, "provenance": provenance}

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
