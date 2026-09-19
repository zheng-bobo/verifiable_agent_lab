"""Small exact vector index used to make retrieval behavior inspectable."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from verifiable_agent_lab.rag.backends import EmbeddingBatch, EmbeddingProvider
from verifiable_agent_lab.rag.types import Chunk, RetrievedChunk


@dataclass(frozen=True)
class SearchResult:
    """Retrieved chunks and query-embedding measurements."""

    chunks: list[RetrievedChunk]
    embedding_tokens: int
    latency_ms: float


class VectorIndex:
    """An in-memory exact cosine index with a portable NumPy cache."""

    def __init__(
        self,
        *,
        chunks: list[Chunk],
        embeddings: NDArray[np.float64],
        embedding_model: str,
        fingerprint: str,
    ) -> None:
        if not chunks:
            raise ValueError("chunks must not be empty")
        if embeddings.ndim != 2 or embeddings.shape[0] != len(chunks):
            raise ValueError("embedding rows must match chunks")
        self.chunks = chunks
        self.embeddings = _normalize_rows(embeddings)
        self.embedding_model = embedding_model
        self.fingerprint = fingerprint

    @classmethod
    def build(cls, chunks: list[Chunk], provider: EmbeddingProvider) -> VectorIndex:
        """Embed chunks and construct an exact-search index."""

        batch = provider.embed([chunk.text for chunk in chunks])
        return cls(
            chunks=chunks,
            embeddings=batch.vectors,
            embedding_model=provider.embedding_model,
            fingerprint=corpus_fingerprint(chunks, provider.embedding_model),
        )

    def search(
        self, query: str, *, top_k: int, provider: EmbeddingProvider
    ) -> SearchResult:
        """Return the ``top_k`` chunks by cosine similarity."""

        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if provider.embedding_model != self.embedding_model:
            raise ValueError("query and index must use the same embedding model")
        query_batch: EmbeddingBatch = provider.embed([query])
        query_vector = _normalize_rows(query_batch.vectors)[0]
        scores = self.embeddings @ query_vector
        count = min(top_k, len(self.chunks))
        order = np.argsort(-scores, kind="stable")[:count]
        retrieved = [
            RetrievedChunk(
                chunk=self.chunks[int(index)],
                score=float(scores[int(index)]),
                rank=rank,
            )
            for rank, index in enumerate(order, start=1)
        ]
        return SearchResult(
            chunks=retrieved,
            embedding_tokens=query_batch.prompt_tokens,
            latency_ms=query_batch.latency_ms,
        )

    def save(self, path: Path) -> None:
        """Save vectors and chunk metadata without Python pickle objects."""

        path.parent.mkdir(parents=True, exist_ok=True)
        metadata = {
            "version": 1,
            "embedding_model": self.embedding_model,
            "fingerprint": self.fingerprint,
            "chunks": [chunk.to_dict() for chunk in self.chunks],
        }
        np.savez_compressed(
            path,
            embeddings=self.embeddings,
            metadata=np.asarray(json.dumps(metadata, ensure_ascii=False)),
        )

    @classmethod
    def load(cls, path: Path) -> VectorIndex:
        """Load an index created by :meth:`save`."""

        with np.load(path, allow_pickle=False) as stored:
            embeddings = np.asarray(stored["embeddings"], dtype=np.float64)
            metadata: dict[str, Any] = json.loads(str(stored["metadata"].item()))
        if metadata.get("version") != 1:
            raise ValueError("unsupported vector-index version")
        return cls(
            chunks=[Chunk.from_dict(item) for item in metadata["chunks"]],
            embeddings=embeddings,
            embedding_model=str(metadata["embedding_model"]),
            fingerprint=str(metadata["fingerprint"]),
        )


def corpus_fingerprint(chunks: list[Chunk], embedding_model: str) -> str:
    """Hash all retrieval inputs to detect a stale cached index."""

    digest = hashlib.sha256(embedding_model.encode())
    for chunk in chunks:
        digest.update(chunk.id.encode())
        digest.update(chunk.text.encode())
    return digest.hexdigest()


def _normalize_rows(vectors: NDArray[np.float64]) -> NDArray[np.float64]:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("embedding vectors must be non-zero")
    return vectors / norms
