"""Repeated-sampling evaluation and artifact generation for the RAG baseline."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from verifiable_agent_lab.rag.pipeline import RAGPipeline, RAGRun, RAGSample


@dataclass(frozen=True)
class EvaluationCase:
    """A deterministic grading rule for one bilingual knowledge-base question."""

    id: str
    question: str
    reference_answer: str
    answer_groups: tuple[tuple[str, ...], ...]
    evidence_groups: tuple[tuple[str, ...], ...]
    expected_sources: tuple[str, ...]
    should_abstain: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationCase:
        return cls(
            id=str(data["id"]),
            question=str(data["question"]),
            reference_answer=str(data["reference_answer"]),
            answer_groups=tuple(tuple(map(str, group)) for group in data["answer_groups"]),
            evidence_groups=tuple(
                tuple(map(str, group)) for group in data.get("evidence_groups", [])
            ),
            expected_sources=tuple(map(str, data.get("expected_sources", []))),
            should_abstain=bool(data.get("should_abstain", False)),
        )


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    """Load and minimally validate the versioned JSON evaluation set."""

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError("evaluation file must contain a non-empty JSON array")
    cases = [EvaluationCase.from_dict(item) for item in data]
    if len({case.id for case in cases}) != len(cases):
        raise ValueError("evaluation case IDs must be unique")
    return cases


def evaluate_pipeline(
    pipeline: RAGPipeline,
    cases: list[EvaluationCase],
    *,
    sample_counts: tuple[int, ...] = (1, 4, 8, 16),
    top_k: int = 4,
    seed: int = 329,
    temperature: float = 0.7,
) -> dict[str, Any]:
    """Retrieve once per case, sample ``max(sample_counts)`` times, and score all prefixes."""

    if not sample_counts or any(count <= 0 for count in sample_counts):
        raise ValueError("sample_counts must contain positive integers")
    if tuple(sorted(set(sample_counts))) != sample_counts:
        raise ValueError("sample_counts must be unique and increasing")

    case_results: list[dict[str, Any]] = []
    runs: list[tuple[EvaluationCase, RAGRun, bool | None, list[dict[str, Any]]]] = []
    maximum = max(sample_counts)
    for case_number, case in enumerate(cases):
        run = pipeline.sample(
            case.question,
            sample_count=maximum,
            top_k=top_k,
            seed=seed + case_number * 1000,
            temperature=temperature,
        )
        retrieval_hit = _retrieval_hit(case, run)
        scored_samples = [
            _score_sample(case, sample, retrieval_hit, run) for sample in run.samples
        ]
        runs.append((case, run, retrieval_hit, scored_samples))
        case_results.append(_serialize_case(case, run, retrieval_hit, scored_samples))

    metrics = [
        _aggregate_at_k(runs, k=count, total_samples=maximum) for count in sample_counts
    ]
    result = {
        "metadata": {
            "created_at": datetime.now(UTC).isoformat(),
            "embedding_model": pipeline.embedding_provider.embedding_model,
            "generation_model": pipeline.generation_provider.generation_model,
            "sample_counts": list(sample_counts),
            "samples_generated_per_question": maximum,
            "top_k": top_k,
            "seed": seed,
            "temperature": temperature,
            "question_count": len(cases),
        },
        "metrics": metrics,
        "cases": case_results,
    }
    result["failures"] = collect_failures(result)
    return result


def estimate_pass_at_k(total: int, correct: int, k: int) -> float:
    """Return the standard unbiased pass@k estimator."""

    if not 0 <= correct <= total:
        raise ValueError("correct must be between zero and total")
    if not 1 <= k <= total:
        raise ValueError("k must be between one and total")
    if total - correct < k:
        return 1.0
    return 1.0 - math.comb(total - correct, k) / math.comb(total, k)


def write_pass_at_k_svg(metrics: list[dict[str, Any]], path: Path) -> None:
    """Write a dependency-free SVG curve from aggregate metric rows."""

    width, height = 720, 440
    left, right, top, bottom = 80, 30, 45, 70
    plot_width = width - left - right
    plot_height = height - top - bottom
    ks = [int(item["k"]) for item in metrics]
    values = [float(item["pass_at_k"]) for item in metrics]
    minimum_k, maximum_k = min(ks), max(ks)

    def x_position(k: int) -> float:
        if minimum_k == maximum_k:
            return left + plot_width / 2
        return left + (k - minimum_k) / (maximum_k - minimum_k) * plot_width

    def y_position(value: float) -> float:
        return top + (1.0 - value) * plot_height

    points = " ".join(
        f"{x_position(k):.1f},{y_position(value):.1f}"
        for k, value in zip(ks, values, strict=True)
    )
    grid: list[str] = []
    for step in range(6):
        value = step / 5
        y = y_position(value)
        grid.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}" '
            'stroke="#d8dee9" stroke-width="1" />'
        )
        grid.append(
            f'<text x="{left-14}" y="{y+5:.1f}" text-anchor="end" '
            f'font-size="13">{value:.1f}</text>'
        )
    labels = "".join(
        f'<text x="{x_position(k):.1f}" y="{height-bottom+28}" text-anchor="middle" '
        f'font-size="13">{k}</text>'
        for k in ks
    )
    circles = "".join(
        f'<circle cx="{x_position(k):.1f}" cy="{y_position(value):.1f}" r="5" '
        'fill="#2563eb" />'
        for k, value in zip(ks, values, strict=True)
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        '<rect width="100%" height="100%" fill="white" />\n'
        f'<text x="{width/2}" y="26" text-anchor="middle" font-family="sans-serif" '
        'font-size="18" font-weight="600">pass@k vs. sample count</text>\n'
        '<g font-family="sans-serif" fill="#1f2937">\n'
        f'{"".join(grid)}\n'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}" '
        'stroke="#374151" />\n'
        f'<line x1="{left}" y1="{height-bottom}" x2="{width-right}" '
        f'y2="{height-bottom}" stroke="#374151" />\n'
        f'<polyline points="{points}" fill="none" stroke="#2563eb" stroke-width="3" />\n'
        f'{circles}\n{labels}\n'
        f'<text x="{width/2}" y="{height-18}" text-anchor="middle" '
        'font-size="14">samples k</text>\n'
        f'<text x="20" y="{height/2}" text-anchor="middle" font-size="14" '
        f'transform="rotate(-90 20 {height/2})">pass@k</text>\n'
        '</g>\n</svg>\n'
    )
    path.write_text(svg, encoding="utf-8")


def write_json(data: dict[str, Any], path: Path) -> None:
    """Write stable, human-readable experiment output."""

    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def collect_failures(result: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Extract concrete failure examples from detailed case records."""

    failures: dict[str, list[dict[str, Any]]] = {
        "invalid_schema": [],
        "retrieval_miss": [],
        "correct_generated_but_not_selected": [],
    }
    sample_counts = result["metadata"]["sample_counts"]
    for case in result["cases"]:
        if case["retrieval_hit"] is False:
            failures["retrieval_miss"].append(
                {"case_id": case["id"], "question": case["question"]}
            )
        for sample_number, sample in enumerate(case["samples"], start=1):
            if not sample["schema_valid"]:
                failures["invalid_schema"].append(
                    {
                        "case_id": case["id"],
                        "sample": sample_number,
                        "error": sample["validation_error"],
                        "raw_output": sample["raw_output"],
                    }
                )
        for k in sample_counts:
            prefix = case["samples"][:k]
            passing = [item for item in prefix if item["pass"]]
            selected = _select_serialized(prefix)
            if passing and selected is not None and not selected["pass"]:
                failures["correct_generated_but_not_selected"].append(
                    {
                        "case_id": case["id"],
                        "k": k,
                        "selected_confidence": selected["confidence"],
                        "correct_sample_count": len(passing),
                    }
                )
    return failures


def _retrieval_hit(case: EvaluationCase, run: RAGRun) -> bool | None:
    if case.should_abstain:
        return None
    retrieved_text = "\n".join(item.chunk.text for item in run.retrieval.chunks).casefold()
    source_hit = not case.expected_sources or any(
        expected in item.chunk.source
        for expected in case.expected_sources
        for item in run.retrieval.chunks
    )
    evidence_hit = _matches_groups(retrieved_text, case.evidence_groups)
    return source_hit and evidence_hit


def _score_sample(
    case: EvaluationCase,
    sample: RAGSample,
    retrieval_hit: bool | None,
    run: RAGRun,
) -> dict[str, Any]:
    value = sample.validation.value
    content_correct = False
    citation_supported = False
    if value is not None:
        content_correct = (
            value.abstained
            if case.should_abstain
            else not value.abstained and _matches_groups(value.answer, case.answer_groups)
        )
        if case.should_abstain:
            citation_supported = value.abstained and not value.citations
        elif value.citations:
            chunk_by_id = {item.chunk.id: item.chunk for item in run.retrieval.chunks}
            cited_chunks = [chunk_by_id[citation] for citation in value.citations]
            cited_text = "\n".join(chunk.text for chunk in cited_chunks)
            source_hit = not case.expected_sources or any(
                expected in chunk.source
                for expected in case.expected_sources
                for chunk in cited_chunks
            )
            citation_supported = source_hit and _matches_groups(
                cited_text, case.evidence_groups
            )
    passed = (
        sample.validation.valid
        and content_correct
        and citation_supported
        and retrieval_hit is not False
    )
    return {
        "seed": sample.seed,
        "raw_output": sample.output.content,
        "schema_valid": sample.validation.valid,
        "validation_error": sample.validation.error,
        "answer": value.answer if value else None,
        "citations": list(value.citations) if value else [],
        "abstained": value.abstained if value else None,
        "confidence": value.confidence if value else None,
        "content_correct": content_correct,
        "citation_supported": citation_supported,
        "pass": passed,
        "prompt_tokens": sample.output.prompt_tokens,
        "completion_tokens": sample.output.completion_tokens,
        "latency_ms": round(sample.output.latency_ms, 3),
        "provider_latency_ms": round(sample.output.provider_latency_ms, 3),
        "cost_usd": sample.output.cost_usd,
        "model": sample.output.model,
    }


def _serialize_case(
    case: EvaluationCase,
    run: RAGRun,
    retrieval_hit: bool | None,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "id": case.id,
        "question": case.question,
        "reference_answer": case.reference_answer,
        "should_abstain": case.should_abstain,
        "retrieval_hit": retrieval_hit,
        "retrieval_latency_ms": round(run.retrieval.latency_ms, 3),
        "retrieval_embedding_tokens": run.retrieval.embedding_tokens,
        "retrieved": [
            {
                "chunk_id": item.chunk.id,
                "source": item.chunk.source,
                "heading": item.chunk.heading,
                "start_line": item.chunk.start_line,
                "end_line": item.chunk.end_line,
                "score": round(item.score, 6),
            }
            for item in run.retrieval.chunks
        ],
        "samples": samples,
    }


def _aggregate_at_k(
    runs: list[tuple[EvaluationCase, RAGRun, bool | None, list[dict[str, Any]]]],
    *,
    k: int,
    total_samples: int,
) -> dict[str, Any]:
    prefix_samples = [sample for _, _, _, samples in runs for sample in samples[:k]]
    selected = [_select_serialized(samples[:k]) for _, _, _, samples in runs]
    selected_existing = [item for item in selected if item is not None]
    pass_estimates = [
        estimate_pass_at_k(total_samples, sum(item["pass"] for item in samples), k)
        for _, _, _, samples in runs
    ]
    answerable = [retrieval for case, _, retrieval, _ in runs if not case.should_abstain]
    diversity = [
        _output_diversity([item["answer"] or item["raw_output"] for item in samples[:k]])
        for _, _, _, samples in runs
    ]
    correct_selected = sum(bool(item and item["pass"]) for item in selected)
    generation_tokens = sum(
        item["prompt_tokens"] + item["completion_tokens"] for item in prefix_samples
    )
    retrieval_tokens = sum(run.retrieval.embedding_tokens for _, run, _, _ in runs)
    total_tokens = generation_tokens + retrieval_tokens
    return {
        "k": k,
        "sample_success_rate": _safe_ratio(
            sum(item["pass"] for item in prefix_samples), len(prefix_samples)
        ),
        "pass_at_k": mean(pass_estimates),
        "coverage_at_k": mean(
            float(any(item["pass"] for item in samples[:k])) for _, _, _, samples in runs
        ),
        "selection_precision": _safe_ratio(
            correct_selected, len(selected_existing)
        ),
        "system_accuracy": _safe_ratio(correct_selected, len(runs)),
        "schema_valid_rate": _safe_ratio(
            sum(item["schema_valid"] for item in prefix_samples), len(prefix_samples)
        ),
        "retrieval_hit_rate": _safe_ratio(
            sum(value is True for value in answerable), len(answerable)
        ),
        "output_diversity": mean(diversity),
        "total_tokens": total_tokens,
        "generation_tokens": generation_tokens,
        "retrieval_embedding_tokens": retrieval_tokens,
        "mean_tokens_per_sample": _safe_ratio(generation_tokens, len(prefix_samples)),
        "mean_latency_ms": mean(item["latency_ms"] for item in prefix_samples),
        "mean_retrieval_latency_ms": mean(run.retrieval.latency_ms for _, run, _, _ in runs),
        "total_cost_usd": sum(item["cost_usd"] for item in prefix_samples),
    }


def _select_serialized(samples: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [item for item in samples if item["schema_valid"]]
    if not valid:
        return None
    return max(valid, key=lambda item: float(item["confidence"]))


def _matches_groups(text: str, groups: tuple[tuple[str, ...], ...]) -> bool:
    normalized = text.casefold()
    return all(any(option.casefold() in normalized for option in group) for group in groups)


def _output_diversity(outputs: list[str]) -> float:
    if len(outputs) < 2:
        return 0.0
    token_sets = [_text_features(output) for output in outputs]
    distances: list[float] = []
    for left in range(len(token_sets)):
        for right in range(left + 1, len(token_sets)):
            union = token_sets[left] | token_sets[right]
            similarity = len(token_sets[left] & token_sets[right]) / len(union) if union else 1.0
            distances.append(1.0 - similarity)
    return mean(distances)


def _text_features(text: str) -> set[str]:
    normalized = re.sub(r"\s+", " ", text.casefold()).strip()
    words = set(re.findall(r"[a-z0-9_]+", normalized))
    cjk = "".join(re.findall(r"[\u3400-\u9fff]", normalized))
    words.update(cjk[index : index + 2] for index in range(max(0, len(cjk) - 1)))
    return words or {normalized}


def _safe_ratio(numerator: int | float, denominator: int) -> float:
    return float(numerator) / denominator if denominator else 0.0
