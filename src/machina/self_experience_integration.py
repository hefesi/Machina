"""Build a cautious autobiographical projection linking experience and Self changes.

The integrator reads the append-only journal and never writes to it. A link is
reported only when supported by explicit event causation or artifact refs.
Repeated change records are reinforcement, not proof of continuous persistence.
"""
from __future__ import annotations

from typing import Any

from .event_store import EventStore
from .self_autobiography import SelfAutobiography


class SelfExperienceIntegrator:
    """Relate recorded experiences to operational Self transformations."""

    def __init__(self, autobiography: SelfAutobiography) -> None:
        if not isinstance(autobiography, SelfAutobiography):
            raise TypeError("autobiography must be a SelfAutobiography")
        self.autobiography = autobiography
        self.event_store: EventStore = autobiography.event_store

    @staticmethod
    def _flatten(value: Any, prefix: str = "") -> dict[str, Any]:
        if isinstance(value, dict) and value:
            result: dict[str, Any] = {}
            for key in sorted(value):
                path = f"{prefix}.{key}" if prefix else str(key)
                result.update(SelfExperienceIntegrator._flatten(value[key], path))
            return result
        return {prefix: value} if prefix else {}

    @classmethod
    def _change_values(cls, record: dict[str, Any]) -> dict[str, dict[str, Any]]:
        change = record.get("content", {}).get("change", {})
        sections = change.get("sections", {}) if isinstance(change, dict) else {}
        values: dict[str, dict[str, Any]] = {}
        for section, pair in sections.items():
            if not isinstance(pair, dict):
                continue
            before = cls._flatten(pair.get("previous"), section)
            after = cls._flatten(pair.get("current"), section)
            for path in sorted(set(before) | set(after)):
                old, new = before.get(path), after.get(path)
                if old != new:
                    values[path] = {"previous": old, "current": new}
        return values

    def integrate(self) -> dict[str, Any]:
        """Return transformation/experience links and conservative durability labels."""
        records = self.autobiography.timeline()
        by_event = {r["event_id"]: r for r in records}
        experiences = [
            r for r in records
            if r["event_type"] in {"experience.recorded", "experience.completed", "action.result", "evaluation.completed"}
            or r["kind"] in {"experience", "evaluation", "action_result"}
        ]
        transformations = [r for r in records if r["event_type"] == "self.transformed"]
        results = []
        for index, current in enumerate(transformations):
            refs = set(current["input_refs"]) | set(current["source_refs"])
            causation = current["causation_id"]
            linked_ids = set()
            if causation in by_event:
                linked_ids.add(causation)
            for candidate in experiences:
                if candidate["event_id"] in refs or candidate["artifact_id"] in refs:
                    linked_ids.add(candidate["event_id"])
            links = [
                {"event_id": event_id, "event_type": by_event[event_id]["event_type"],
                 "link_basis": "explicit_causation" if event_id == causation else "explicit_artifact_reference"}
                for event_id in sorted(linked_ids, key=lambda item: by_event[item]["sequence"])
            ]
            changes = self._change_values(current)
            later = transformations[index + 1:]
            durability = {}
            for path, change in changes.items():
                repeated = 0
                reversed_later = False
                for future in later:
                    future_change = self._change_values(future).get(path)
                    if future_change is None:
                        continue
                    if future_change["current"] == change["current"]:
                        repeated += 1
                    elif future_change["previous"] == change["current"]:
                        reversed_later = True
                if reversed_later:
                    status = "reversed"
                elif repeated:
                    status = "reinforced"
                else:
                    status = "observed_once"
                durability[path] = {
                    "status": status,
                    "matching_later_transformations": repeated,
                    "basis": "subsequent_self_transformation_records_only",
                }
            results.append({
                "event_id": current["event_id"],
                "sequence": current["sequence"],
                "cycle_id": current["cycle_id"],
                "trigger": current["content"].get("change", {}).get("trigger"),
                "evidence_refs": current["content"].get("evidence_refs", []),
                "experience_links": links,
                "changes": changes,
                "durability": durability,
                "epistemic_status": "inferred",
            })
        return {
            "experience_count": len(experiences),
            "transformation_count": len(transformations),
            "transformations": results,
            "unlinked_transformations": [
                item["event_id"] for item in results if not item["experience_links"]
            ],
            "epistemic_note": (
                "Links require explicit journal causation or artifact references. "
                "Repeated transformation records indicate reinforcement, not proof "
                "that a state persisted continuously between observations. "
                "This projection does not establish subjective experience."
            ),
        }

    def trace(self, event_id: str) -> dict[str, Any] | None:
        """Return one integrated transformation by its exact journal event ID."""
        return next(
            (item for item in self.integrate()["transformations"]
             if item["event_id"] == event_id),
            None,
        )
