"""Minimal retrieval-augmented generation components."""

from verifiable_agent_lab.rag.chunking import ChunkerConfig, chunk_documents
from verifiable_agent_lab.rag.documents import load_markdown_documents
from verifiable_agent_lab.rag.index import VectorIndex
from verifiable_agent_lab.rag.pipeline import RAGPipeline
from verifiable_agent_lab.rag.types import Chunk, Document, RetrievedChunk

__all__ = [
    "Chunk",
    "ChunkerConfig",
    "Document",
    "RAGPipeline",
    "RetrievedChunk",
    "VectorIndex",
    "chunk_documents",
    "load_markdown_documents",
]
