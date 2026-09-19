"""Model-provider interfaces and a dependency-free Ollama HTTP backend."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray


class BackendError(RuntimeError):
    """Raised when a model backend cannot satisfy a request."""


@dataclass(frozen=True)
class EmbeddingBatch:
    """Embedding vectors plus provider-reported usage."""

    vectors: NDArray[np.float64]
    prompt_tokens: int = 0
    latency_ms: float = 0.0


@dataclass(frozen=True)
class GenerationOutput:
    """Raw model output and measurements needed by the evaluator."""

    content: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    provider_latency_ms: float
    cost_usd: float
    model: str


class EmbeddingProvider(Protocol):
    """Interface used by indexing and query retrieval."""

    @property
    def embedding_model(self) -> str: ...

    def embed(self, texts: list[str]) -> EmbeddingBatch: ...


class GenerationProvider(Protocol):
    """Interface used by repeated sampling."""

    @property
    def generation_model(self) -> str: ...

    def generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        seed: int,
        temperature: float,
    ) -> GenerationOutput: ...


class OllamaBackend:
    """Use Ollama's local ``/api/embed`` and ``/api/chat`` endpoints.

    No Ollama Python package is required. The server reports token counts and
    nanosecond durations, which are preserved for experiment accounting.
    """

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        embedding_model: str = "qwen3-embedding:0.6b",
        generation_model: str = "qwen3:4b",
        timeout_seconds: float = 180.0,
        embedding_batch_size: int = 32,
        input_cost_per_million: float = 0.0,
        output_cost_per_million: float = 0.0,
    ) -> None:
        if embedding_batch_size <= 0:
            raise ValueError("embedding_batch_size must be positive")
        self.base_url = base_url.rstrip("/")
        self._embedding_model = embedding_model
        self._generation_model = generation_model
        self.timeout_seconds = timeout_seconds
        self.embedding_batch_size = embedding_batch_size
        self.input_cost_per_million = input_cost_per_million
        self.output_cost_per_million = output_cost_per_million

    @property
    def embedding_model(self) -> str:
        return self._embedding_model

    @property
    def generation_model(self) -> str:
        return self._generation_model

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        if not texts:
            raise ValueError("texts must not be empty")
        started = time.perf_counter()
        batches: list[NDArray[np.float64]] = []
        prompt_tokens = 0
        for start in range(0, len(texts), self.embedding_batch_size):
            inputs = texts[start : start + self.embedding_batch_size]
            response = self._post(
                "/api/embed",
                {"model": self.embedding_model, "input": inputs, "truncate": False},
            )
            vectors = np.asarray(response.get("embeddings"), dtype=np.float64)
            if vectors.ndim != 2 or vectors.shape[0] != len(inputs):
                raise BackendError("Ollama returned an invalid embedding matrix")
            batches.append(vectors)
            prompt_tokens += int(response.get("prompt_eval_count", 0))
        wall_ms = (time.perf_counter() - started) * 1000
        return EmbeddingBatch(
            vectors=np.vstack(batches),
            prompt_tokens=prompt_tokens,
            latency_ms=wall_ms,
        )

    def generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        seed: int,
        temperature: float,
    ) -> GenerationOutput:
        started = time.perf_counter()
        response = self._post(
            "/api/chat",
            {
                "model": self.generation_model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the supplied evidence. Return JSON matching the "
                            "provided schema. If evidence is insufficient, abstain."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "format": schema,
                "think": False,
                "options": {"seed": seed, "temperature": temperature},
            },
        )
        wall_ms = (time.perf_counter() - started) * 1000
        message = response.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise BackendError("Ollama returned an invalid chat response")
        prompt_tokens = int(response.get("prompt_eval_count", 0))
        completion_tokens = int(response.get("eval_count", 0))
        cost = (
            prompt_tokens * self.input_cost_per_million
            + completion_tokens * self.output_cost_per_million
        ) / 1_000_000
        return GenerationOutput(
            content=message["content"],
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=wall_ms,
            provider_latency_ms=float(response.get("total_duration", 0)) / 1_000_000,
            cost_usd=cost,
            model=self.generation_model,
        )

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise BackendError(f"Ollama HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise BackendError(
                f"cannot reach Ollama at {self.base_url}; start Ollama and pull the models"
            ) from error
        except json.JSONDecodeError as error:
            raise BackendError("Ollama returned non-JSON data") from error
        if not isinstance(decoded, dict):
            raise BackendError("Ollama returned a non-object response")
        return decoded
