"""Tool contracts and small deterministic tools for the teaching harness."""

from __future__ import annotations

import ast
import math
import operator
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from verifiable_agent_lab.harness.schema import validate_arguments
from verifiable_agent_lab.harness.types import ToolResult
from verifiable_agent_lab.rag.backends import EmbeddingProvider
from verifiable_agent_lab.rag.index import VectorIndex


class ToolExecutionError(RuntimeError):
    """A deterministic tool error that should be shown to the model."""


class RetryableToolError(ToolExecutionError):
    """A transient tool failure that the harness may retry automatically."""


@dataclass(frozen=True)
class ToolSpec:
    """Model-visible tool description plus harness-owned execution metadata."""

    name: str
    description: str
    input_schema: dict[str, Any]
    timeout_seconds: float = 5.0
    read_only: bool = True

    def to_model_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class Tool(Protocol):
    """A capability that can be registered with the harness."""

    @property
    def spec(self) -> ToolSpec: ...

    def execute(self, arguments: dict[str, Any]) -> ToolResult: ...


class ToolRegistry:
    """Expose an allowlisted subset and validate all calls before dispatch."""

    def __init__(self, tools: list[Tool], *, allowed_tools: set[str] | None = None) -> None:
        by_name = {tool.spec.name: tool for tool in tools}
        if len(by_name) != len(tools):
            raise ValueError("tool names must be unique")
        requested = allowed_tools if allowed_tools is not None else set(by_name)
        unknown = requested - set(by_name)
        if unknown:
            raise ValueError(f"allowlist contains unknown tools: {sorted(unknown)}")
        self._tools = by_name
        self._allowed = frozenset(requested)

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._allowed)

    @property
    def specs(self) -> list[ToolSpec]:
        return [self._tools[name].spec for name in self.tool_names]

    def invoke(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if name not in self._allowed:
            raise ToolExecutionError(f"tool is not allowed: {name}")
        tool = self._tools[name]
        try:
            validate_arguments(arguments, tool.spec.input_schema)
        except ValueError as error:
            raise ToolExecutionError(f"invalid arguments for {name}: {error}") from error
        return tool.execute(arguments)


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class CalculatorTool:
    """Evaluate arithmetic expressions without Python ``eval``."""

    spec = ToolSpec(
        name="calculator",
        description=(
            "Evaluate one finite arithmetic expression. Supports +, -, *, /, //, %, **, "
            "parentheses, integers, and decimal numbers; no variables or functions."
        ),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"expression": {"type": "string", "minLength": 1}},
            "required": ["expression"],
        },
    )

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        expression = str(arguments["expression"])
        if len(expression) > 200:
            raise ToolExecutionError("calculator expression exceeds 200 characters")
        try:
            tree = ast.parse(expression, mode="eval")
            value = _evaluate_arithmetic(tree.body)
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError) as error:
            raise ToolExecutionError(f"invalid arithmetic expression: {error}") from error
        if isinstance(value, float) and not math.isfinite(value):
            raise ToolExecutionError("calculator result must be finite")
        if abs(value) > 1e100:
            raise ToolExecutionError("calculator result is too large")
        return ToolResult({"expression": expression, "value": value})


def _evaluate_arithmetic(node: ast.expr) -> int | float:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, int | float):
            raise ValueError("only numeric constants are allowed")
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate_arithmetic(node.left)
        right = _evaluate_arithmetic(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent magnitude cannot exceed 100")
        return _BINARY_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate_arithmetic(node.operand))
    raise ValueError(f"unsupported expression node: {type(node).__name__}")


class DocumentSearchTool:
    """Expose the Week 2 exact-vector retrieval pipeline as a read-only tool."""

    spec = ToolSpec(
        name="document_search",
        description=(
            "Search the repository's bilingual reading notes. Returns ranked chunks with "
            "source paths, headings, line ranges, and similarity scores."
        ),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "query": {"type": "string", "minLength": 1},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 8},
            },
            "required": ["query"],
        },
        timeout_seconds=30.0,
    )

    def __init__(
        self,
        *,
        index: VectorIndex,
        embedding_provider: EmbeddingProvider,
        default_top_k: int = 4,
        max_chunk_chars: int = 1_500,
    ) -> None:
        self.index = index
        self.embedding_provider = embedding_provider
        self.default_top_k = default_top_k
        self.max_chunk_chars = max_chunk_chars

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments["query"])
        top_k = int(arguments.get("top_k", self.default_top_k))
        result = self.index.search(query, top_k=top_k, provider=self.embedding_provider)
        matches = [
            {
                "id": item.chunk.id,
                "rank": item.rank,
                "score": round(item.score, 6),
                "source": item.chunk.source,
                "heading": item.chunk.heading,
                "lines": [item.chunk.start_line, item.chunk.end_line],
                "text": item.chunk.text[: self.max_chunk_chars],
            }
            for item in result.chunks
        ]
        return ToolResult(
            {
                "query": query,
                "matches": matches,
                "embedding_tokens": result.embedding_tokens,
                "latency_ms": result.latency_ms,
            }
        )


_BANNED_PYTHON_NODES = (
    ast.AsyncFunctionDef,
    ast.AsyncWith,
    ast.Attribute,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.Nonlocal,
    ast.Raise,
    ast.Try,
    ast.While,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)
_SAFE_CALLS = {
    "abs",
    "all",
    "any",
    "bool",
    "dict",
    "enumerate",
    "float",
    "int",
    "len",
    "list",
    "max",
    "min",
    "print",
    "range",
    "round",
    "set",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
}
_PYTHON_WORKER = """
import builtins
import sys

safe_names = {safe_names!r}
safe_builtins = {{name: getattr(builtins, name) for name in safe_names}}
namespace = {{"__builtins__": safe_builtins}}
code = sys.stdin.read()
try:
    exec(compile(code, "<agent-python>", "exec"), namespace, namespace)
except BaseException as error:
    print(f"{{type(error).__name__}}: {{error}}", file=sys.stderr)
    raise SystemExit(1)
""".strip().format(safe_names=sorted(_SAFE_CALLS))


class RestrictedPythonTool:
    """Run a small Python subset in an isolated subprocess and temp directory.

    This is a teaching boundary, not a hardened OS sandbox. Production code
    should additionally use container/VM isolation, filesystem and network
    policies, resource limits, and explicit approvals.
    """

    spec = ToolSpec(
        name="python_runner",
        description=(
            "Run a restricted Python snippet for pure computation and assertions. Imports, "
            "attribute access, file/network access, classes, and unbounded while loops are "
            "rejected. This is not a production security sandbox."
        ),
        input_schema={
            "type": "object",
            "additionalProperties": False,
            "properties": {"code": {"type": "string", "minLength": 1}},
            "required": ["code"],
        },
        timeout_seconds=3.0,
    )

    def __init__(self, *, max_code_chars: int = 4_000, max_output_chars: int = 4_000) -> None:
        self.max_code_chars = max_code_chars
        self.max_output_chars = max_output_chars

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        code = str(arguments["code"])
        if len(code) > self.max_code_chars:
            raise ToolExecutionError(f"Python code exceeds {self.max_code_chars} characters")
        _validate_python_subset(code)
        try:
            with tempfile.TemporaryDirectory(prefix="verifiable-agent-python-") as directory:
                completed = subprocess.run(
                    [sys.executable, "-I", "-S", "-c", _PYTHON_WORKER],
                    input=code,
                    text=True,
                    capture_output=True,
                    cwd=Path(directory),
                    env={"PYTHONIOENCODING": "utf-8"},
                    timeout=self.spec.timeout_seconds,
                    check=False,
                )
        except subprocess.TimeoutExpired as error:
            raise ToolExecutionError(
                f"Python execution exceeded {self.spec.timeout_seconds:.1f} seconds"
            ) from error
        stdout = completed.stdout[: self.max_output_chars]
        stderr = completed.stderr[: self.max_output_chars]
        result = {
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "output_truncated": (
                len(completed.stdout) > self.max_output_chars
                or len(completed.stderr) > self.max_output_chars
            ),
        }
        if completed.returncode != 0:
            detail = stderr.strip() or stdout.strip()
            raise ToolExecutionError(f"restricted Python failed: {detail}")
        return ToolResult(result)


def _validate_python_subset(code: str) -> None:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as error:
        raise ToolExecutionError(f"invalid Python syntax: {error.msg}") from error
    for node in ast.walk(tree):
        if isinstance(node, _BANNED_PYTHON_NODES):
            raise ToolExecutionError(f"Python node is not allowed: {type(node).__name__}")
        if isinstance(node, ast.Name) and node.id.startswith("_"):
            raise ToolExecutionError("names beginning with '_' are not allowed")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_CALLS:
                raise ToolExecutionError("only allowlisted builtin calls are permitted")
            if any(keyword.arg is None for keyword in node.keywords):
                raise ToolExecutionError("expanded keyword arguments are not permitted")


def tool_specs_as_dicts(registry: ToolRegistry) -> list[dict[str, Any]]:
    """Return JSON-serializable specs for prompts and trace metadata."""

    return [asdict(spec) for spec in registry.specs]
