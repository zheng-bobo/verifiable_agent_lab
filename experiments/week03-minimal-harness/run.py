"""Run the Week 3 minimal observe-decide-act harness."""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path
from typing import Any

from verifiable_agent_lab.harness import (
    AgentHarness,
    CalculatorTool,
    DocumentSearchTool,
    HarnessConfig,
    OllamaDecisionProvider,
    RestrictedPythonTool,
    RunLimits,
    ScriptedDecisionProvider,
    ToolRegistry,
)
from verifiable_agent_lab.harness.tools import ToolResult, ToolSpec
from verifiable_agent_lab.rag.backends import OllamaBackend
from verifiable_agent_lab.rag.chunking import ChunkerConfig, chunk_documents
from verifiable_agent_lab.rag.documents import load_markdown_documents
from verifiable_agent_lab.rag.index import VectorIndex, corpus_fingerprint

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = Path(__file__).resolve().parent


class FixtureDocumentSearch:
    """Offline stand-in used only to demonstrate the complete event loop."""

    spec = ToolSpec(
        name="document_search",
        description="Search a deterministic fixture that represents the bilingual notes.",
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["query"],
        },
    )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        return ToolResult(
            {
                "query": arguments["query"],
                "matches": [
                    {
                        "source": "week03-tool-use-and-harness.zh-CN.md",
                        "heading": "MCP",
                        "text": "MCP standardizes how hosts connect models to tools and context.",
                    }
                ],
                "fixture": True,
            }
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("fixture", "ollama"), default="fixture")
    parser.add_argument(
        "--task",
        default="先查询笔记说明 MCP 的作用，再计算 6 * 7，并综合回答。",
    )
    parser.add_argument("--base-url", default="http://localhost:11434")
    parser.add_argument("--embedding-model", default="qwen3-embedding:0.6b")
    parser.add_argument("--generation-model", default="qwen3:4b")
    parser.add_argument("--notes-root", type=Path, default=ROOT / "docs" / "readings")
    parser.add_argument(
        "--index", type=Path, default=ROOT / "data" / "processed" / "week03-harness-index.npz"
    )
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-tool-calls", type=int, default=8)
    parser.add_argument("--max-total-tokens", type=int, default=16_000)
    parser.add_argument("--max-seconds", type=float, default=120.0)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=329)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.backend == "fixture":
        provider = ScriptedDecisionProvider(
            [
                {
                    "type": "tool_call",
                    "tool_name": "document_search",
                    "arguments": {"query": "MCP Model Context Protocol"},
                },
                {
                    "type": "tool_call",
                    "tool_name": "calculator",
                    "arguments": {"expression": "6 * 7"},
                },
                {
                    "type": "finish",
                    "answer": "MCP 标准化模型与外部工具、上下文的连接；6 * 7 = 42。",
                },
            ]
        )
        search_tool: FixtureDocumentSearch | DocumentSearchTool = FixtureDocumentSearch()
    else:
        embedding_backend = OllamaBackend(
            base_url=args.base_url,
            embedding_model=args.embedding_model,
            generation_model=args.generation_model,
        )
        index = load_or_build_index(
            args.notes_root,
            args.index,
            embedding_backend,
            rebuild=args.rebuild_index,
        )
        search_tool = DocumentSearchTool(
            index=index,
            embedding_provider=embedding_backend,
        )
        provider = OllamaDecisionProvider(
            base_url=args.base_url,
            model=args.generation_model,
        )

    registry = ToolRegistry(
        [CalculatorTool(), RestrictedPythonTool(), search_tool],
        allowed_tools={"calculator", "python_runner", "document_search"},
    )
    config = HarnessConfig(
        limits=RunLimits(
            max_steps=args.max_steps,
            max_model_calls=args.max_steps + 2,
            max_tool_calls=args.max_tool_calls,
            max_total_tokens=args.max_total_tokens,
            max_elapsed_seconds=args.max_seconds,
        ),
        seed=args.seed,
        temperature=args.temperature,
    )
    trace_path = args.trace or (
        ROOT / "runs" / "week03-minimal-harness" / f"{args.backend}-{uuid.uuid4().hex}.jsonl"
    )
    run = AgentHarness(provider=provider, tools=registry, config=config).run(
        args.task,
        trace_path=trace_path,
    )
    print(
        json.dumps(
            {
                "run_id": run.run_id,
                "status": run.status,
                "answer": run.answer,
                "reason": run.reason,
                "usage": run.usage.to_dict(),
                "trace": str(trace_path),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def load_or_build_index(
    notes_root: Path,
    index_path: Path,
    backend: OllamaBackend,
    *,
    rebuild: bool,
) -> VectorIndex:
    documents = load_markdown_documents(notes_root.resolve())
    chunks = chunk_documents(documents, ChunkerConfig())
    expected = corpus_fingerprint(chunks, backend.embedding_model)
    if index_path.exists() and not rebuild:
        cached = VectorIndex.load(index_path)
        if cached.fingerprint == expected:
            return cached
    index = VectorIndex.build(chunks, backend)
    index.save(index_path)
    return index


if __name__ == "__main__":
    main()
