from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class MNNEventProjectionResult:
    scanned_count: int
    projected_count: int
    already_projected_count: int
    last_sequence: int
