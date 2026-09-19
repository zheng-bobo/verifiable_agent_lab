"""Retrieval, grounded prompting, structured generation, and sampling."""

from __future__ import annotations

from dataclasses import dataclass

from verifiable_agent_lab.rag.backends import (
    EmbeddingProvider,
    GenerationOutput,
    GenerationProvider,
)
from verifiable_agent_lab.rag.index import SearchResult, VectorIndex
from verifiable_agent_lab.rag.schema import ValidationResult, answer_schema, validate_answer
from verifiable_agent_lab.rag.types import RetrievedChunk


@dataclass(frozen=True)
class RAGSample:
    """One independently sampled answer to a fixed retrieval result."""

    seed: int
    output: GenerationOutput
    validation: ValidationResult


@dataclass(frozen=True)
class RAGRun:
    """One retrieval followed by one or more model samples."""

    question: str
    retrieval: SearchResult
    samples: list[RAGSample]


class RAGPipeline:
    """Minimal inspectable RAG pipeline with no orchestration framework."""

    def __init__(
        self,
        *,
        index: VectorIndex,
        embedding_provider: EmbeddingProvider,
        generation_provider: GenerationProvider,
    ) -> None:
        self.index = index
        self.embedding_provider = embedding_provider
        self.generation_provider = generation_provider

    def sample(
        self,
        question: str,
        *,
        sample_count: int,
        top_k: int = 4,
        seed: int = 329,
        temperature: float = 0.7,
    ) -> RAGRun:
        """Retrieve once, then sample the generator with consecutive seeds."""

        if sample_count <= 0:
            raise ValueError("sample_count must be positive")
        retrieval = self.index.search(question, top_k=top_k, provider=self.embedding_provider)
        prompt = build_grounded_prompt(question, retrieval.chunks)
        allowed = [item.chunk.id for item in retrieval.chunks]
        schema = answer_schema(allowed)
        samples: list[RAGSample] = []
        for offset in range(sample_count):
            sample_seed = seed + offset
            output = self.generation_provider.generate(
                prompt,
                schema=schema,
                seed=sample_seed,
                temperature=temperature,
            )
            samples.append(
                RAGSample(
                    seed=sample_seed,
                    output=output,
                    validation=validate_answer(output.content, set(allowed)),
                )
            )
        return RAGRun(question=question, retrieval=retrieval, samples=samples)


def build_grounded_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    """Render retrieved evidence with stable, schema-valid citation IDs."""

    evidence = "\n\n".join(_render_chunk(item) for item in chunks)
    return (
        "Use only the evidence below. Answer in the language of the question. "
        "Cite chunk IDs exactly. If the evidence cannot answer the question, set "
        "abstained to true, explain the gap briefly, and return no citations.\n\n"
        f"<evidence>\n{evidence}\n</evidence>\n\n"
        f"<question>\n{question}\n</question>\n\n"
        "Return only the JSON object required by the schema."
    )


def _render_chunk(item: RetrievedChunk) -> str:
    chunk = item.chunk
    return (
        f"<chunk id=\"{chunk.id}\" source=\"{chunk.source}\" "
        f"lines=\"{chunk.start_line}-{chunk.end_line}\" rank=\"{item.rank}\">\n"
        f"{chunk.text}\n</chunk>"
    )
