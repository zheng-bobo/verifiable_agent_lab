from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from verifiable_agent_lab.harness import (
    AgentHarness,
    CalculatorTool,
    HarnessConfig,
    RestrictedPythonTool,
    RetryPolicy,
    RunLimits,
    ScriptedDecisionProvider,
    ToolRegistry,
)
from verifiable_agent_lab.harness.events import EventLog
from verifiable_agent_lab.harness.loop import build_decision_prompt
from verifiable_agent_lab.harness.schema import action_schema
from verifiable_agent_lab.harness.tools import (
    DocumentSearchTool,
    RetryableToolError,
    ToolExecutionError,
    ToolSpec,
)
from verifiable_agent_lab.harness.types import ToolResult
from verifiable_agent_lab.rag.backends import EmbeddingBatch
from verifiable_agent_lab.rag.index import VectorIndex
from verifiable_agent_lab.rag.types import Chunk


def test_harness_runs_observe_decide_act_loop_and_writes_jsonl(tmp_path: Path) -> None:
    provider = ScriptedDecisionProvider(
        [
            {"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "6*7"}},
            {"type": "finish", "answer": "The result is 42."},
        ]
    )
    trace_path = tmp_path / "trace.jsonl"
    harness = AgentHarness(provider=provider, tools=ToolRegistry([CalculatorTool()]))

    run = harness.run("Calculate 6*7.", trace_path=trace_path, run_id="run-1")

    assert run.status == "success"
    assert run.answer == "The result is 42."
    assert run.usage.steps == 2
    assert run.usage.tool_calls == 1
    assert [event["sequence"] for event in run.events] == list(range(1, len(run.events) + 1))
    stored = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert stored == list(run.events)
    assert any(
        event["type"] == "observation"
        and event["data"].get("content", {}).get("value") == 42
        for event in run.events
    )


def test_invalid_model_action_becomes_observation_then_model_can_recover() -> None:
    provider = ScriptedDecisionProvider(
        [
            "not JSON",
            {"type": "finish", "answer": "Recovered after validation feedback."},
        ]
    )
    harness = AgentHarness(provider=provider, tools=ToolRegistry([CalculatorTool()]))

    run = harness.run("Finish safely.")

    assert run.status == "success"
    assert any(
        event["type"] == "observation"
        and "action_error" in event["data"].get("content", {})
        for event in run.events
    )


def test_step_budget_stops_an_unfinished_loop() -> None:
    provider = ScriptedDecisionProvider(
        [
            {"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "1+1"}},
            {"type": "finish", "answer": "2"},
        ]
    )
    config = HarnessConfig(limits=RunLimits(max_steps=1))
    harness = AgentHarness(
        provider=provider,
        tools=ToolRegistry([CalculatorTool()]),
        config=config,
    )

    run = harness.run("Keep going.")

    assert run.status == "budget_exhausted"
    assert run.reason == "step budget exhausted"


@dataclass
class FlakyTool:
    calls: int = 0
    spec = ToolSpec(
        name="flaky",
        description="Fail transiently once, then return a value.",
        input_schema={"type": "object", "additionalProperties": False},
    )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        del arguments
        self.calls += 1
        if self.calls == 1:
            raise RetryableToolError("temporary outage")
        return ToolResult({"value": "ok"})


@dataclass
class BrokenTool:
    spec = ToolSpec(
        name="broken",
        description="Raise an unexpected implementation error.",
        input_schema={"type": "object", "additionalProperties": False},
    )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        del arguments
        raise KeyError("missing internal state")


def test_retryable_tool_error_uses_bounded_retry() -> None:
    tool = FlakyTool()
    provider = ScriptedDecisionProvider(
        [
            {"type": "tool_call", "tool_name": "flaky", "arguments": {}},
            {"type": "finish", "answer": "Recovered."},
        ]
    )
    config = HarnessConfig(
        tool_retry=RetryPolicy(max_attempts=2, initial_delay_seconds=0),
    )
    harness = AgentHarness(
        provider=provider,
        tools=ToolRegistry([tool]),
        config=config,
        sleep=lambda _: None,
    )

    run = harness.run("Call the flaky tool.")

    assert run.status == "success"
    assert tool.calls == 2
    assert run.usage.tool_calls == 2
    assert any(event["type"] == "tool_retry" for event in run.events)


def test_retry_cannot_cross_tool_call_budget() -> None:
    tool = FlakyTool()
    provider = ScriptedDecisionProvider(
        [{"type": "tool_call", "tool_name": "flaky", "arguments": {}}]
    )
    config = HarnessConfig(
        limits=RunLimits(max_tool_calls=1, max_cost_usd=0),
        tool_retry=RetryPolicy(max_attempts=2, initial_delay_seconds=0),
    )
    harness = AgentHarness(
        provider=provider,
        tools=ToolRegistry([tool]),
        config=config,
        sleep=lambda _: None,
    )

    run = harness.run("Call the flaky tool.")

    assert run.status == "budget_exhausted"
    assert run.reason == "tool-call budget exhausted during retry"
    assert run.usage.tool_calls == 1


def test_identical_successful_tool_call_is_not_executed_twice() -> None:
    provider = ScriptedDecisionProvider(
        [
            {"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "2+2"}},
            {"type": "tool_call", "tool_name": "calculator", "arguments": {"expression": "2+2"}},
            {"type": "finish", "answer": "4"},
        ]
    )
    harness = AgentHarness(provider=provider, tools=ToolRegistry([CalculatorTool()]))

    run = harness.run("Calculate 2+2 once.")

    assert run.status == "success"
    assert run.usage.tool_calls == 1
    assert any(
        "duplicate tool call rejected" in event["data"].get("content", {}).get("error", "")
        for event in run.events
        if event["type"] == "observation"
    )


def test_unexpected_tool_exception_becomes_recoverable_observation() -> None:
    provider = ScriptedDecisionProvider(
        [
            {"type": "tool_call", "tool_name": "broken", "arguments": {}},
            {"type": "finish", "answer": "Reported the failure safely."},
        ]
    )
    harness = AgentHarness(provider=provider, tools=ToolRegistry([BrokenTool()]))

    run = harness.run("Try the broken tool and recover.")

    assert run.status == "success"
    assert any(
        "unexpected broken failure: KeyError" in event["data"].get("content", {}).get("error", "")
        for event in run.events
        if event["type"] == "observation"
    )


def test_calculator_and_python_runner_reject_unsafe_inputs() -> None:
    calculator = CalculatorTool()
    python = RestrictedPythonTool()

    assert calculator.execute({"expression": "(2 + 3) ** 2"}).content["value"] == 25
    with pytest.raises(ToolExecutionError, match="unsupported expression"):
        calculator.execute({"expression": "open('/tmp/file')"})
    with pytest.raises(ToolExecutionError, match="Import"):
        python.execute({"code": "import os"})
    result = python.execute({"code": "values = [1, 2, 3]\nprint(sum(values))"})
    assert result.content["stdout"] == "6\n"


class KeywordEmbedder:
    embedding_model = "keyword-test"

    def embed(self, texts: list[str]) -> EmbeddingBatch:
        vectors = np.asarray(
            [[1.0 + text.lower().count("mcp"), 1.0 + text.lower().count("rag")] for text in texts]
        )
        return EmbeddingBatch(vectors=vectors)


def test_document_search_tool_reuses_vector_index() -> None:
    chunks = [
        Chunk("mcp", "d1", "mcp.md", "en", "MCP", "MCP tool protocol", 1, 2),
        Chunk("rag", "d2", "rag.md", "en", "RAG", "RAG retrieval", 1, 2),
    ]
    embedder = KeywordEmbedder()
    tool = DocumentSearchTool(
        index=VectorIndex.build(chunks, embedder),
        embedding_provider=embedder,
    )

    result = tool.execute({"query": "MCP", "top_k": 1})

    assert result.content["matches"][0]["id"] == "mcp"


def test_action_schema_embeds_each_tools_argument_contract() -> None:
    schema = action_schema(
        [("calculator", CalculatorTool.spec.input_schema), ("flaky", FlakyTool.spec.input_schema)]
    )

    calculator_branch = schema["oneOf"][0]
    assert calculator_branch["properties"]["tool_name"] == {"const": "calculator"}
    assert calculator_branch["properties"]["arguments"] == CalculatorTool.spec.input_schema


def test_prompt_derives_completed_tools_only_from_successful_tool_observations() -> None:
    log = EventLog()
    log.append("run", "observation", step=0, source="user", content={"task": "x"}, is_error=False)
    log.append(
        "run",
        "observation",
        step=1,
        source="calculator",
        content={"value": 4},
        is_error=False,
    )
    log.append(
        "run",
        "observation",
        step=2,
        source="document_search",
        content={"error": "timeout"},
        is_error=True,
    )

    prompt = build_decision_prompt(
        "x",
        ToolRegistry([CalculatorTool()]),
        log.events,
        max_observations=12,
    )

    assert '<completed_tools>\n["calculator"]\n</completed_tools>' in prompt
