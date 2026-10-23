"""Atomic JSON checkpoints for preserving an MNN's learned state.

A checkpoint stores the complete versioned MNN snapshot: topology, connection
weights, unit states, activation functions, and timestep. It does not claim
that a snapshot is a trained general-purpose model.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from .mnn import MNN


class MNNCheckpointStore:
    """Save and restore validated MNN snapshots using atomic file replacement."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def save(self, network: MNN) -> None:
        """Validate and atomically persist the network snapshot."""
        snapshot = network.snapshot()
        # Validate the serialized contract before it can replace a good checkpoint.
        MNN.from_snapshot(snapshot)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary_path = temporary.name
                json.dump(snapshot, temporary, ensure_ascii=False, sort_keys=True)
                temporary.write("\n")
                temporary.flush()
                os.fsync(temporary.fileno())
            os.replace(temporary_path, self.path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    os.unlink(temporary_path)
                except FileNotFoundError:
                    pass

    def load(self) -> MNN:
        """Load a checkpoint and validate it through the MNN snapshot contract."""
        with self.path.open("r", encoding="utf-8") as source:
            try:
                snapshot = json.load(source)
            except json.JSONDecodeError as error:
                raise ValueError(f"invalid MNN checkpoint JSON: {self.path}") from error
        if not isinstance(snapshot, dict):
            raise ValueError("MNN checkpoint must contain a JSON object")
        return MNN.from_snapshot(snapshot)
