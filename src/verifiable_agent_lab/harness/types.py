"""Shared data structures for the minimal agent harness."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal, TypeAlias


@dataclass(frozen=True)
class ToolCallAction:
    """A model request to invoke one registered tool."""

    type: Literal["tool_call"]
    tool_name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class FinishAction:
    """A model request to finish the run with a user-facing answer."""

    type: Literal["finish"]
    answer: str


AgentAction: TypeAlias = ToolCallAction | FinishAction


@dataclass(frozen=True)
class DecisionOutput:
    """Raw model decision and provider usage measurements."""

    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    model: str = "unknown"


@dataclass(frozen=True)
class ToolResult:
    """Structured result returned by a deterministic tool adapter."""

    content: dict[str, Any]
    is_error: bool = False


@dataclass(frozen=True)
class RunLimits:
    """Hard limits enforced by the harness rather than by the model."""

    max_steps: int = 8
    max_model_calls: int = 10
    max_tool_calls: int = 8
    max_total_tokens: int = 16_000
    max_cost_usd: float = 1.0
    max_elapsed_seconds: float = 120.0

    def __post_init__(self) -> None:
        numeric_limits = {
            "max_steps": self.max_steps,
            "max_model_calls": self.max_model_calls,
            "max_tool_calls": self.max_tool_calls,
            "max_total_tokens": self.max_total_tokens,
            "max_elapsed_seconds": self.max_elapsed_seconds,
        }
        if any(value <= 0 for value in numeric_limits.values()):
            raise ValueError("all run limits except max_cost_usd must be positive")
        if self.max_cost_usd < 0:
            raise ValueError("max_cost_usd must be non-negative")


@dataclass
class RunUsage:
    """Mutable counters owned exclusively by the harness."""

    steps: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> dict[str, int | float]:
        return asdict(self)


@dataclass(frozen=True)
class RetryPolicy:
    """Bounded exponential backoff for transient infrastructure errors."""

    max_attempts: int = 3
    initial_delay_seconds: float = 0.25
    multiplier: float = 2.0
    max_delay_seconds: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts <= 0:
            raise ValueError("max_attempts must be positive")
        if self.initial_delay_seconds < 0 or self.max_delay_seconds < 0:
            raise ValueError("retry delays must be non-negative")
        if self.multiplier < 1:
            raise ValueError("retry multiplier must be at least 1")

    def delay_before(self, next_attempt: int) -> float:
        """Return the delay before a one-indexed retry attempt."""

        if next_attempt <= 1:
            return 0.0
        delay = self.initial_delay_seconds * self.multiplier ** (next_attempt - 2)
        return min(delay, self.max_delay_seconds)


RunStatus = Literal["success", "failure", "budget_exhausted"]


@dataclass(frozen=True)
class HarnessRun:
    """Terminal result plus the event stream needed for inspection."""

    run_id: str
    status: RunStatus
    answer: str | None
    reason: str
    usage: RunUsage
    events: tuple[dict[str, Any], ...] = field(default_factory=tuple)
