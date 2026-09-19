from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from verifiable_agent_lab.rag.backends import EmbeddingBatch, GenerationOutput
from verifiable_agent_lab.rag.evaluation import (
    EvaluationCase,
    estimate_pass_at_k,
    evaluate_pipeline,
    write_pass_at_k_svg,
)
from verifiable_agent_lab.rag.index import VectorIndex
from verifiable_agent_lab.rag.pipeline import RAGPipeline
from verifiable_agent_lab.rag.types import Chunk


class AlphaEmbedder:
    embedding_model = "alpha-test"

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        return EmbeddingBatch(
            vectors=np.asarray([[1.0 + text.casefold().count("alpha"), 1.0] for text in texts])
        )


class SelectionFailureGenerator:
    generation_model = "selection-failure-test"

    def __init__(self) -> None:
        self.call = 0

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
        pattern = self.call
        self.call += 1
        if pattern == 2:
            content = "not-json"
        else:
            correct = pattern in {0, 3}
            content = json.dumps(
                {
                    "answer": "right alpha answer" if correct else "wrong answer",
                    "citations": [citation],
                    "abstained": False,
                    "confidence": 0.5 if correct else 0.99,
                }
            )
        return GenerationOutput(content, 10, 5, 1.0, 1.0, 0.0, self.generation_model)


def test_pass_at_k_estimator() -> None:
    assert estimate_pass_at_k(4, 2, 1) == pytest.approx(0.5)
    assert estimate_pass_at_k(4, 2, 4) == 1.0


def test_evaluation_distinguishes_coverage_from_selection(tmp_path: Path) -> None:
    chunk = Chunk("alpha", "doc", "note.md", "en", "Alpha", "alpha evidence", 1, 2)
    embedder = AlphaEmbedder()
    pipeline = RAGPipeline(
        index=VectorIndex.build([chunk], embedder),
        embedding_provider=embedder,
        generation_provider=SelectionFailureGenerator(),
    )
    case = EvaluationCase(
        id="alpha",
        question="alpha?",
        reference_answer="right alpha answer",
        answer_groups=(("right",),),
        evidence_groups=(("alpha",),),
        expected_sources=("note.md",),
    )

    result = evaluate_pipeline(pipeline, [case], sample_counts=(1, 4), top_k=1)
    at_four = result["metrics"][1]
    curve = tmp_path / "curve.svg"
    write_pass_at_k_svg(result["metrics"], curve)

    assert at_four["coverage_at_k"] == 1.0
    assert at_four["selection_precision"] == 0.0
    assert at_four["system_accuracy"] == 0.0
    assert result["failures"]["invalid_schema"]
    assert result["failures"]["correct_generated_but_not_selected"]
    assert "<svg" in curve.read_text(encoding="utf-8")
