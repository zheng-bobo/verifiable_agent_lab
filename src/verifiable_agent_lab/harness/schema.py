"""Strict local validation for model actions and tool inputs."""

from __future__ import annotations

import json
import math
from typing import Any

from verifiable_agent_lab.harness.types import AgentAction, FinishAction, ToolCallAction


def action_schema(tool_inputs: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """Build the exact JSON Schema sent to a structured-output backend."""

    if not tool_inputs:
        raise ValueError("at least one tool must be available")
    tool_branches = [
        {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "type": {"const": "tool_call"},
                "tool_name": {"const": name},
                "arguments": input_schema,
            },
            "required": ["type", "tool_name", "arguments"],
        }
        for name, input_schema in tool_inputs
    ]
    return {
        "oneOf": [
            *tool_branches,
            {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "type": {"const": "finish"},
                    "answer": {"type": "string", "minLength": 1},
                },
                "required": ["type", "answer"],
            },
        ]
    }


def parse_action(raw: str, allowed_tools: set[str]) -> AgentAction:
    """Parse model JSON while enforcing the same boundary locally."""

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid action JSON: {error.msg}") from error
    if not isinstance(data, dict):
        raise ValueError("action must be a JSON object")

    action_type = data.get("type")
    if action_type == "tool_call":
        if set(data) != {"type", "tool_name", "arguments"}:
            raise ValueError("tool_call keys do not match the action schema")
        tool_name = data["tool_name"]
        arguments = data["arguments"]
        if not isinstance(tool_name, str) or tool_name not in allowed_tools:
            raise ValueError(f"tool is not allowed: {tool_name!r}")
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be a JSON object")
        return ToolCallAction("tool_call", tool_name, arguments)

    if action_type == "finish":
        if set(data) != {"type", "answer"}:
            raise ValueError("finish keys do not match the action schema")
        answer = data["answer"]
        if not isinstance(answer, str) or not answer.strip():
            raise ValueError("finish answer must be a non-empty string")
        return FinishAction("finish", answer.strip())

    raise ValueError("action type must be 'tool_call' or 'finish'")


def validate_arguments(arguments: dict[str, Any], schema: dict[str, Any]) -> None:
    """Validate the small JSON Schema subset used by this teaching harness."""

    if schema.get("type") != "object":
        raise ValueError("tool input schema must describe an object")
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    if not isinstance(properties, dict) or not isinstance(required, set):
        raise ValueError("invalid tool input schema")

    missing = required - set(arguments)
    if missing:
        raise ValueError(f"missing required arguments: {', '.join(sorted(missing))}")
    if schema.get("additionalProperties") is False:
        unexpected = set(arguments) - set(properties)
        if unexpected:
            raise ValueError(f"unexpected arguments: {', '.join(sorted(unexpected))}")

    for name, value in arguments.items():
        property_schema = properties.get(name)
        if property_schema is None:
            continue
        _validate_value(value, property_schema, path=name)


def _validate_value(value: Any, schema: dict[str, Any], *, path: str) -> None:
    expected = schema.get("type")
    if not isinstance(expected, str):
        raise ValueError(f"argument {path!r} has an invalid schema type")
    valid = {
        "string": isinstance(value, str),
        "number": isinstance(value, int | float) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }.get(expected, True)
    if not valid:
        raise ValueError(f"argument {path!r} must be {expected}")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"argument {path!r} is not an allowed value")
    if isinstance(value, str) and len(value) < int(schema.get("minLength", 0)):
        raise ValueError(f"argument {path!r} is too short")
    if isinstance(value, int | float) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            raise ValueError(f"argument {path!r} must be finite")
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"argument {path!r} is below the minimum")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"argument {path!r} exceeds the maximum")
