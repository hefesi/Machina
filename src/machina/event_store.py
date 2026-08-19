"""Append-only SQLite event journal.

The journal is the source of truth.  Mutable projections can always be
rebuilt from it, which is the practical meaning of "do not lose anything in
the loop" for this first implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from threading import RLock
from typing import Any, Iterable

from .contracts import Artifact, ContractError, canonical_json, new_id, now_utc


class IntegrityError(RuntimeError):
    """Raised when the append-only journal has a broken hash chain."""


class CycleNotFoundError(KeyError):
    """Raised when a caller refers to an unknown cognitive cycle."""


@dataclass(frozen=True, slots=True)
class StoredEvent:
    sequence: int
    event_id: str
    cycle_id: str
    event_type: str
    artifact: Artifact
    created_at: str
    causation_id: str | None
    previous_hash: str | None
    event_hash: str


class EventStore:
    """A durable, immutable event store backed only by Python's stdlib."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()
        self._connection = sqlite3.connect(
            self.path, isolation_level=None, check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        self._initialise()

    def _initialise(self) -> None:
        with self._lock:
            self._connection.execute("PRAGMA foreign_keys = ON")
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = FULL")
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS cycles (
                    cycle_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    schema_version TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    cycle_id TEXT NOT NULL REFERENCES cycles(cycle_id),
                    event_type TEXT NOT NULL,
                    artifact_id TEXT NOT NULL UNIQUE,
                    artifact_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    causation_id TEXT,
                    previous_hash TEXT,
                    event_hash TEXT NOT NULL UNIQUE
                );

                CREATE INDEX IF NOT EXISTS events_cycle_sequence_idx
                    ON events(cycle_id, sequence);
                CREATE INDEX IF NOT EXISTS events_type_idx
                    ON events(event_type, sequence);

                CREATE TRIGGER IF NOT EXISTS events_are_append_only_update
                BEFORE UPDATE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'events are append-only');
                END;

                CREATE TRIGGER IF NOT EXISTS events_are_append_only_delete
                BEFORE DELETE ON events
                BEGIN
                    SELECT RAISE(ABORT, 'events are append-only');
                END;
                """
            )

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    def __enter__(self) -> "EventStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def create_cycle(self, cycle_id: str, *, schema_version: str = "0.1") -> None:
        with self._lock:
            self._connection.execute(
                "INSERT OR IGNORE INTO cycles(cycle_id, created_at, schema_version) VALUES (?, ?, ?)",
                (cycle_id, now_utc(), schema_version),
            )

    def has_cycle(self, cycle_id: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM cycles WHERE cycle_id = ?", (cycle_id,)
        ).fetchone()
        return row is not None

    def append(
        self,
        event_type: str,
        artifact: Artifact,
        *,
        causation_id: str | None = None,
    ) -> StoredEvent:
        """Commit one event atomically, chaining it to the prior journal event."""

        if not self.has_cycle(artifact.cycle_id):
            raise CycleNotFoundError(artifact.cycle_id)
        if not event_type:
            raise ContractError("event_type is required")

        with self._lock:
            cursor = self._connection.cursor()
            try:
                cursor.execute("BEGIN IMMEDIATE")
                previous_row = cursor.execute(
                    "SELECT event_hash FROM events ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                previous_hash = previous_row["event_hash"] if previous_row else None
                event_id = new_id("event")
                created_at = now_utc()
                hash_input = {
                    "event_id": event_id,
                    "cycle_id": artifact.cycle_id,
                    "event_type": event_type,
                    "artifact": artifact.to_dict(),
                    "created_at": created_at,
                    "causation_id": causation_id,
                    "previous_hash": previous_hash,
                }
                event_hash = sha256(canonical_json(hash_input).encode("utf-8")).hexdigest()
                cursor.execute(
                    """
                    INSERT INTO events(
                        event_id, cycle_id, event_type, artifact_id, artifact_json,
                        created_at, causation_id, previous_hash, event_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        artifact.cycle_id,
                        event_type,
                        artifact.id,
                        canonical_json(artifact.to_dict()),
                        created_at,
                        causation_id,
                        previous_hash,
                        event_hash,
                    ),
                )
                sequence = int(cursor.lastrowid)
                cursor.execute("COMMIT")
            except BaseException:
                cursor.execute("ROLLBACK")
                raise

        return StoredEvent(
            sequence=sequence,
            event_id=event_id,
            cycle_id=artifact.cycle_id,
            event_type=event_type,
            artifact=artifact,
            created_at=created_at,
            causation_id=causation_id,
            previous_hash=previous_hash,
            event_hash=event_hash,
        )

    def events_for_cycle(self, cycle_id: str) -> list[StoredEvent]:
        if not self.has_cycle(cycle_id):
            raise CycleNotFoundError(cycle_id)
        rows = self._connection.execute(
            "SELECT * FROM events WHERE cycle_id = ? ORDER BY sequence", (cycle_id,)
        ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def all_events(self) -> list[StoredEvent]:
        rows = self._connection.execute("SELECT * FROM events ORDER BY sequence").fetchall()
        return [self._row_to_event(row) for row in rows]

    def latest_artifact(self, cycle_id: str, event_type: str) -> Artifact | None:
        row = self._connection.execute(
            """
            SELECT * FROM events
            WHERE cycle_id = ? AND event_type = ?
            ORDER BY sequence DESC LIMIT 1
            """,
            (cycle_id, event_type),
        ).fetchone()
        return self._row_to_event(row).artifact if row else None

    def artifacts_for_event_types(self, event_types: Iterable[str]) -> list[Artifact]:
        event_types = tuple(event_types)
        if not event_types:
            return []
        placeholders = ",".join("?" for _ in event_types)
        rows = self._connection.execute(
            f"SELECT * FROM events WHERE event_type IN ({placeholders}) ORDER BY sequence",
            event_types,
        ).fetchall()
        return [self._row_to_event(row).artifact for row in rows]

    def verify_integrity(self) -> None:
        """Verify the whole hash chain and the artifact/event cross-links."""

        previous_hash: str | None = None
        seen_artifact_ids: set[str] = set()
        for event in self.all_events():
            if event.artifact.id in seen_artifact_ids:
                raise IntegrityError(f"duplicate artifact id: {event.artifact.id}")
            seen_artifact_ids.add(event.artifact.id)
            if event.previous_hash != previous_hash:
                raise IntegrityError(
                    f"broken previous hash at event {event.sequence} ({event.event_id})"
                )
            hash_input = {
                "event_id": event.event_id,
                "cycle_id": event.cycle_id,
                "event_type": event.event_type,
                "artifact": event.artifact.to_dict(),
                "created_at": event.created_at,
                "causation_id": event.causation_id,
                "previous_hash": event.previous_hash,
            }
            expected_hash = sha256(canonical_json(hash_input).encode("utf-8")).hexdigest()
            if event.event_hash != expected_hash:
                raise IntegrityError(
                    f"invalid event hash at event {event.sequence} ({event.event_id})"
                )
            previous_hash = event.event_hash

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> StoredEvent:
        return StoredEvent(
            sequence=int(row["sequence"]),
            event_id=str(row["event_id"]),
            cycle_id=str(row["cycle_id"]),
            event_type=str(row["event_type"]),
            artifact=Artifact.from_dict(json.loads(row["artifact_json"])),
            created_at=str(row["created_at"]),
            causation_id=row["causation_id"],
            previous_hash=row["previous_hash"],
            event_hash=str(row["event_hash"]),
        )
