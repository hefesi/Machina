"""D2.5: demonstrate answering supported queries and abstaining on ambiguity."""
from __future__ import annotations

import json

from machina.confidence_policy import decide
from machina.transfer_benchmark import TRANSFER_TASKS, TransferTask


def run_demo() -> dict[str, object]:
    supported = [decide(task) for task in TRANSFER_TASKS]
    ambiguous = TransferTask(
        "ambiguous",
        "- Ivo — editor: Helix\n- Ivo — editor: Vim",
        "Find editor belonging to Ivo.",
        "UNRESOLVABLE",
    )
    unsupported = TransferTask(
        "unsupported",
        "Ivo's editor might be Helix, but this note is not a structured record.",
        "Find editor belonging to Ivo.",
        "UNRESOLVABLE",
    )
    ambiguous_decision = decide(ambiguous)
    unsupported_decision = decide(unsupported)
    passed = (
        all(item.status == "answered" and item.answer == task.expected_answer
            for item, task in zip(supported, TRANSFER_TASKS))
        and ambiguous_decision.status == "abstained_ambiguous"
        and ambiguous_decision.answer is None
        and unsupported_decision.status == "abstained_no_evidence"
        and unsupported_decision.answer is None
    )
    return {
        "experiment": "d2_5_confidence_and_abstention",
        "supported_queries": len(supported),
        "supported_correct": sum(
            item.answer == task.expected_answer
            for item, task in zip(supported, TRANSFER_TASKS)
        ),
        "ambiguous_status": ambiguous_decision.status,
        "ambiguous_candidates": list(ambiguous_decision.candidates),
        "unsupported_status": unsupported_decision.status,
        "passed": passed,
        "scope": (
            "Tests deterministic evidence-based abstention on supported record "
            "formats. The confidence value is not a calibrated probability and "
            "the policy is not a general-purpose language understanding system."
        ),
    }


if __name__ == "__main__":
    result = run_demo()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if not result["passed"]:
        raise SystemExit(1)
