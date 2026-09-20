"""Append-only JSONL event storage for agent runs."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class EventLog:
    """Write every state transition before the next transition begins."""

    def __init__(
        self,
        path: Path | None = None,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.path = path
        self.clock = clock or (lambda: datetime.now(UTC))
        self._events: list[dict[str, Any]] = []
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._events)

    def append(self, run_id: str, event_type: str, **data: Any) -> dict[str, Any]:
        event = {
            "sequence": len(self._events) + 1,
            "timestamp": self.clock().isoformat(),
            "run_id": run_id,
            "type": event_type,
            "data": data,
        }
        self._events.append(event)
        if self.path is not None:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
                handle.flush()
        return event
