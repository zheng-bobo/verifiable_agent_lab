from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from verifiable_agent_lab.rag.backends import EmbeddingBatch, GenerationOutput, OllamaBackend
from verifiable_agent_lab.rag.index import VectorIndex
from verifiable_agent_lab.rag.pipeline import RAGPipeline
from verifiable_agent_lab.rag.schema import validate_answer
from verifiable_agent_lab.rag.types import Chunk


class KeywordEmbedder:
    embedding_model = "keyword-test"

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        vectors = np.asarray(
            [
                [
                    1.0 + text.casefold().count("retrieval"),
                    1.0 + text.casefold().count("harness"),
                ]
                for text in texts
            ]
        )
        return EmbeddingBatch(vectors=vectors, prompt_tokens=len(texts), latency_ms=1.0)


class CitingGenerator:
    generation_model = "citing-test"

    def generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        seed: int,
        temperature: float,
    ) -> GenerationOutput:
        del prompt, seed, temperature
        citation = schema["properties"]["citations"]["items"]["enum"][0]
        content = json.dumps(
            {
                "answer": "Retrieval finds evidence.",
                "citations": [citation],
                "abstained": False,
                "confidence": 0.8,
            }
        )
        return GenerationOutput(content, 10, 5, 2.0, 1.5, 0.0, self.generation_model)


def make_chunks() -> list[Chunk]:
    return [
        Chunk("a", "d1", "retrieval.md", "en", "Retrieval", "retrieval evidence", 1, 2),
        Chunk("b", "d2", "harness.md", "en", "Harness", "harness state", 1, 2),
    ]


def test_vector_index_search_and_round_trip(tmp_path: Path) -> None:
    provider = KeywordEmbedder()
    index = VectorIndex.build(make_chunks(), provider)

    result = index.search("retrieval", top_k=1, provider=provider)
    index_path = tmp_path / "index.npz"
    index.save(index_path)
    loaded = VectorIndex.load(index_path)

    assert result.chunks[0].chunk.id == "a"
    assert loaded.fingerprint == index.fingerprint
    assert loaded.search("harness", top_k=1, provider=provider).chunks[0].chunk.id == "b"


def test_pipeline_returns_locally_validated_json() -> None:
    embedder = KeywordEmbedder()
    pipeline = RAGPipeline(
        index=VectorIndex.build(make_chunks(), embedder),
        embedding_provider=embedder,
        generation_provider=CitingGenerator(),
    )

    run = pipeline.sample("What does retrieval do?", sample_count=2, top_k=1)

    assert len(run.samples) == 2
    assert all(sample.validation.valid for sample in run.samples)
    assert run.samples[0].validation.value is not None
    assert run.samples[0].validation.value.citations == ("a",)


def test_schema_validator_rejects_invalid_and_unretrieved_citations() -> None:
    invalid_json = validate_answer("{broken", {"a"})
    invented_citation = validate_answer(
        json.dumps(
            {
                "answer": "answer",
                "citations": ["invented"],
                "abstained": False,
                "confidence": 0.5,
            }
        ),
        {"a"},
    )

    assert not invalid_json.valid
    assert invalid_json.error is not None and "invalid JSON" in invalid_json.error
    assert not invented_citation.valid
    assert invented_citation.error == "response cites a chunk that was not retrieved"


def test_ollama_backend_batches_embeddings_and_records_usage(monkeypatch: Any) -> None:
    requests: list[dict[str, Any]] = []

    class FakeResponse:
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload).encode()

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        del timeout
        payload = json.loads(bytes(request.data or b"{}").decode())
        requests.append(payload)
        if request.full_url.endswith("/api/embed"):
            inputs = payload["input"]
            return FakeResponse(
                {
                    "embeddings": [[float(index + 1), 1.0] for index in range(len(inputs))],
                    "prompt_eval_count": len(inputs),
                }
            )
        return FakeResponse(
            {
                "message": {"content": "{}"},
                "prompt_eval_count": 10,
                "eval_count": 5,
                "total_duration": 2_000_000,
            }
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    backend = OllamaBackend(
        embedding_batch_size=2,
        input_cost_per_million=1.0,
        output_cost_per_million=2.0,
    )

    embedded = backend.embed(["one", "two", "three"])
    generated = backend.generate("prompt", schema={"type": "object"}, seed=7, temperature=0.2)

    assert embedded.vectors.shape == (3, 2)
    assert embedded.prompt_tokens == 3
    assert [len(request["input"]) for request in requests[:2]] == [2, 1]
    assert requests[2]["model"] == "qwen3:4b"
    assert requests[2]["format"] == {"type": "object"}
    assert requests[2]["think"] is False
    assert generated.provider_latency_ms == 2.0
    assert generated.cost_usd == pytest.approx(0.00002)
