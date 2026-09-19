"""Run the Week 2 bilingual RAG repeated-sampling evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from verifiable_agent_lab.rag.backends import EmbeddingBatch, GenerationOutput, OllamaBackend
from verifiable_agent_lab.rag.chunking import ChunkerConfig, chunk_documents
from verifiable_agent_lab.rag.documents import load_markdown_documents
from verifiable_agent_lab.rag.evaluation import (
    EvaluationCase,
    evaluate_pipeline,
    load_evaluation_cases,
    write_json,
    write_pass_at_k_svg,
)
from verifiable_agent_lab.rag.index import VectorIndex, corpus_fingerprint
from verifiable_agent_lab.rag.pipeline import RAGPipeline

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = Path(__file__).resolve().parent
EXCLUDED_KB_SOURCES = {
    "week02-raglite-reference.md",
    "week02-raglite-reference.zh-CN.md",
}


class FixtureBackend:
    """Deterministic harness fixture; never use its numbers as model results."""

    embedding_model = "fixture-feature-hash-v1"
    generation_model = "fixture-scripted-v1"

    def __init__(self, cases: list[EvaluationCase], dimensions: int = 4096) -> None:
        self.cases = {case.question: case for case in cases}
        self.dimensions = dimensions
        self.calls: defaultdict[str, int] = defaultdict(int)

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        rows = np.zeros((len(texts), self.dimensions), dtype=np.float64)
        for row, text in enumerate(texts):
            for feature in _features(text):
                digest = hashlib.blake2b(feature.encode(), digest_size=8).digest()
                index = int.from_bytes(digest, "little") % self.dimensions
                rows[row, index] += 1.0
        return EmbeddingBatch(vectors=rows, prompt_tokens=sum(len(text) // 4 for text in texts))

    def generate(
        self,
        prompt: str,
        *,
        schema: dict[str, Any],
        seed: int,
        temperature: float,
    ) -> GenerationOutput:
        del seed, temperature
        question_match = re.search(r"<question>\n(.*?)\n</question>", prompt, re.DOTALL)
        if question_match is None:
            raise ValueError("fixture prompt does not contain a question")
        question = question_match.group(1).strip()
        case = self.cases[question]
        call_index = self.calls[question]
        self.calls[question] += 1
        citation = _supporting_citation(prompt, case, schema)

        pattern = call_index % 4
        if pattern == 2:
            content = "{this is deliberately invalid JSON"
        elif pattern in {0, 3}:
            content = json.dumps(
                {
                    "answer": case.reference_answer,
                    "citations": [] if case.should_abstain else [citation],
                    "abstained": case.should_abstain,
                    "confidence": 0.55 if pattern == 0 else 0.75,
                },
                ensure_ascii=False,
            )
        else:
            content = json.dumps(
                {
                    "answer": "The retrieved notes support a different conclusion.",
                    "citations": [citation],
                    "abstained": False,
                    "confidence": 0.95,
                },
                ensure_ascii=False,
            )
        return GenerationOutput(
            content=content,
            prompt_tokens=max(1, len(prompt) // 4),
            completion_tokens=max(1, len(content) // 4),
            latency_ms=12.0 + call_index,
            provider_latency_ms=10.0 + call_index,
            cost_usd=0.0,
            model=self.generation_model,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("ollama", "fixture"), default="ollama")
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--embedding-model", default="qwen3-embedding:0.6b")
    parser.add_argument("--generation-model", default="qwen3:4b")
    parser.add_argument("--notes-root", type=Path, default=ROOT / "docs" / "readings")
    parser.add_argument("--questions", type=Path, default=EXPERIMENT_DIR / "questions.json")
    parser.add_argument(
        "--index", type=Path, default=ROOT / "data" / "processed" / "week02-rag-index.npz"
    )
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--top-k", type=int, default=4)
    parser.add_argument("--max-chars", type=int, default=1200)
    parser.add_argument("--overlap-chars", type=int, default=160)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--seed", type=int, default=329)
    parser.add_argument("--input-cost-per-million", type=float, default=0.0)
    parser.add_argument("--output-cost-per-million", type=float, default=0.0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--curve", type=Path)
    parser.add_argument("--failures", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cases = load_evaluation_cases(args.questions)
    notes_root = args.notes_root.resolve()
    documents = [
        document
        for document in load_markdown_documents(notes_root)
        if document.source not in EXCLUDED_KB_SOURCES
    ]
    chunks = chunk_documents(
        documents,
        ChunkerConfig(max_chars=args.max_chars, overlap_chars=args.overlap_chars),
    )
    if args.backend == "fixture":
        backend: FixtureBackend | OllamaBackend = FixtureBackend(cases)
    else:
        backend = OllamaBackend(
            base_url=args.base_url,
            embedding_model=args.embedding_model,
            generation_model=args.generation_model,
            input_cost_per_million=args.input_cost_per_million,
            output_cost_per_million=args.output_cost_per_million,
        )

    index = _load_or_build_index(
        chunks,
        backend,
        args.index,
        rebuild=args.rebuild_index or args.backend == "fixture",
        persist=args.backend == "ollama",
    )
    pipeline = RAGPipeline(
        index=index,
        embedding_provider=backend,
        generation_provider=backend,
    )
    result = evaluate_pipeline(
        pipeline,
        cases,
        top_k=args.top_k,
        seed=args.seed,
        temperature=args.temperature,
    )
    result["metadata"].update(
        {
            "backend": args.backend,
            "notes_root": (
                notes_root.relative_to(ROOT).as_posix()
                if notes_root.is_relative_to(ROOT)
                else notes_root.as_posix()
            ),
            "excluded_sources": sorted(EXCLUDED_KB_SOURCES),
            "document_count": len(documents),
            "chunk_count": len(chunks),
            "chunk_max_chars": args.max_chars,
            "chunk_overlap_chars": args.overlap_chars,
            "scientific_result": args.backend != "fixture",
        }
    )

    prefix = "fixture-" if args.backend == "fixture" else ""
    output_path = args.output or EXPERIMENT_DIR / f"{prefix}results.json"
    curve_path = args.curve or EXPERIMENT_DIR / f"{prefix}pass-at-k.svg"
    failures_path = args.failures or EXPERIMENT_DIR / f"{prefix}failures.json"
    write_json(result, output_path)
    write_pass_at_k_svg(result["metrics"], curve_path)
    write_json(
        {"metadata": result["metadata"], "failures": result["failures"]},
        failures_path,
    )
    print(f"Wrote {output_path}")
    print(f"Wrote {curve_path}")
    print(f"Wrote {failures_path}")


def _load_or_build_index(
    chunks: list[Any],
    backend: FixtureBackend | OllamaBackend,
    path: Path,
    *,
    rebuild: bool,
    persist: bool,
) -> VectorIndex:
    expected = corpus_fingerprint(chunks, backend.embedding_model)
    if path.exists() and not rebuild:
        cached = VectorIndex.load(path)
        if cached.fingerprint == expected:
            return cached
    index = VectorIndex.build(chunks, backend)
    if persist:
        index.save(path)
    return index


def _features(text: str) -> set[str]:
    normalized = text.casefold()
    features = set(re.findall(r"[a-z0-9_]+", normalized))
    cjk_runs = re.findall(r"[\u3400-\u9fff]+", normalized)
    for run in cjk_runs:
        features.update(run[index : index + 2] for index in range(max(1, len(run) - 1)))
    return features or {normalized}


def _supporting_citation(
    prompt: str, case: EvaluationCase, schema: dict[str, Any]
) -> str:
    allowed = schema["properties"]["citations"]["items"]["enum"]
    for chunk_id, text in re.findall(
        r'<chunk id="([^"]+)"[^>]*>\n(.*?)\n</chunk>', prompt, re.DOTALL
    ):
        normalized = text.casefold()
        if all(
            any(option.casefold() in normalized for option in group)
            for group in case.evidence_groups
        ):
            return chunk_id
    return str(allowed[0])


if __name__ == "__main__":
    main()
