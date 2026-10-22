"""Persistent, provenance-aware knowledge storage and lexical retrieval.

This module is the first knowledge layer for Machina. It stores material supplied
by the user or by an external acquisition adapter; it does not fetch the public
internet itself and it does not claim semantic understanding.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


_TOKEN_RE = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in _TOKEN_RE.findall(text)]


def _finite_confidence(value: float) -> float:
    if isinstance(value, bool):
        raise ValueError("confidence must be a finite number between 0 and 1")
    confidence = float(value)
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise ValueError("confidence must be a finite number between 0 and 1")
    return confidence


def _json_object(value: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"metadata must be finite JSON data: {error}") from error


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """A stored document with an explicit origin and epistemic confidence."""

    id: str
    title: str
    content: str
    source_uri: str
    source_type: str
    confidence: float
    metadata: Mapping[str, Any]
    created_at: str


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    """A document retrieved for a query; score is lexical relevance, not truth."""

    document: KnowledgeDocument
    score: float
    matched_terms: tuple[str, ...]


class DuplicateKnowledgeError(ValueError):
    """Raised when an existing document ID would be overwritten implicitly."""


class KnowledgeStore:
    """SQLite-backed document store with deterministic, provenance-aware search.

    Search uses normalized token overlap with a title boost. It is a transparent
    baseline for retrieval, not embeddings, web search, or a truth verifier.
    Document writes are explicit and each row preserves its source and metadata.
    """

    schema_version = 1

    def __init__(self, storage_path: str | Path) -> None:
        path = str(storage_path)
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 5000")
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_uri TEXT NOT NULL,
                source_type TEXT NOT NULL,
                confidence REAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
                metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_source ON knowledge_documents(source_uri)"
        )
        self._connection.commit()
        self._closed = False

    def close(self) -> None:
        if not self._closed:
            self._connection.close()
            self._closed = True

    def __enter__(self) -> "KnowledgeStore":
        if self._closed:
            raise RuntimeError("knowledge store is closed")
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def add_document(
        self,
        *,
        title: str,
        content: str,
        source_uri: str,
        source_type: str = "user",
        confidence: float = 1.0,
        metadata: Mapping[str, Any] | None = None,
        document_id: str | None = None,
    ) -> KnowledgeDocument:
        """Persist one document; duplicate IDs fail rather than silently overwrite."""
        self._ensure_open()
        if not isinstance(title, str) or not title.strip():
            raise ValueError("title must be a non-empty string")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be a non-empty string")
        if not isinstance(source_uri, str) or not source_uri.strip():
            raise ValueError("source_uri must be a non-empty string identifying provenance")
        if not isinstance(source_type, str) or not source_type.strip():
            raise ValueError("source_type must be a non-empty string")
        confidence_value = _finite_confidence(confidence)
        metadata_value = dict(metadata or {})
        metadata_json = _json_object(metadata_value)
        identifier = document_id or f"knowledge_{uuid4().hex}"
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("document_id must be a non-empty string")
        created_at = datetime.now(timezone.utc).isoformat()
        try:
            self._connection.execute(
                """
                INSERT INTO knowledge_documents
                (id, title, content, source_uri, source_type, confidence, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    identifier, title.strip(), content.strip(), source_uri.strip(),
                    source_type.strip(), confidence_value, metadata_json, created_at,
                ),
            )
            self._connection.commit()
        except sqlite3.IntegrityError as error:
            self._connection.rollback()
            if "UNIQUE constraint failed" in str(error) or "PRIMARY KEY" in str(error):
                raise DuplicateKnowledgeError(
                    f"document ID already exists: {identifier}"
                ) from error
            raise
        return self.get_document(identifier)

    def get_document(self, document_id: str) -> KnowledgeDocument:
        self._ensure_open()
        row = self._connection.execute(
            "SELECT * FROM knowledge_documents WHERE id = ?", (document_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"unknown knowledge document: {document_id}")
        return self._from_row(row)

    def search(self, query: str, *, limit: int = 5) -> list[KnowledgeHit]:
        """Search stored documents only; returns stable relevance ordering."""
        self._ensure_open()
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be a non-empty string")
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        query_terms = set(_tokens(query))
        if not query_terms:
            return []
        rows = self._connection.execute(
            "SELECT * FROM knowledge_documents ORDER BY created_at, id"
        ).fetchall()
        hits: list[KnowledgeHit] = []
        for row in rows:
            document = self._from_row(row)
            body_terms = set(_tokens(document.content))
            title_terms = set(_tokens(document.title))
            matched = query_terms & (body_terms | title_terms)
            if not matched:
                continue
            body_score = len(query_terms & body_terms) / len(query_terms | body_terms)
            title_score = len(query_terms & title_terms) / len(query_terms)
            score = min(1.0, body_score + 0.35 * title_score)
            hits.append(KnowledgeHit(
                document=document,
                score=score,
                matched_terms=tuple(sorted(matched)),
            ))
        hits.sort(key=lambda hit: (-hit.score, -hit.document.confidence, hit.document.id))
        return hits[:limit]

    def count(self) -> int:
        self._ensure_open()
        return int(self._connection.execute(
            "SELECT COUNT(*) FROM knowledge_documents"
        ).fetchone()[0])

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("knowledge store is closed")

    @staticmethod
    def _from_row(row: sqlite3.Row) -> KnowledgeDocument:
        return KnowledgeDocument(
            id=str(row["id"]),
            title=str(row["title"]),
            content=str(row["content"]),
            source_uri=str(row["source_uri"]),
            source_type=str(row["source_type"]),
            confidence=float(row["confidence"]),
            metadata=json.loads(row["metadata_json"]),
            created_at=str(row["created_at"]),
        )
