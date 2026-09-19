"""Shared immutable data structures for the RAG pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class Document:
    """A Markdown document loaded from the knowledge base."""

    id: str
    source: str
    language: str
    title: str
    text: str


@dataclass(frozen=True)
class Chunk:
    """A stable, citable section of a source document."""

    id: str
    document_id: str
    source: str
    language: str
    heading: str
    text: str
    start_line: int
    end_line: int

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        """Reconstruct a chunk stored in an index manifest."""

        return cls(
            id=str(data["id"]),
            document_id=str(data["document_id"]),
            source=str(data["source"]),
            language=str(data["language"]),
            heading=str(data["heading"]),
            text=str(data["text"]),
            start_line=int(data["start_line"]),
            end_line=int(data["end_line"]),
        )


@dataclass(frozen=True)
class RetrievedChunk:
    """A chunk returned by exact cosine-similarity search."""

    chunk: Chunk
    score: float
    rank: int
