from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol


class EventSink(Protocol):
    def emit(self, task_id: str, kind: str, data: dict[str, Any]) -> None:
        ...


class SQLiteEventSink:
    def __init__(self, store) -> None:
        self.store = store

    def emit(self, task_id: str, kind: str, data: dict[str, Any]) -> None:
        self.store.save_event(
            task_id,
            kind,
            data,
            datetime.now(timezone.utc).isoformat(),
        )


class NullEventSink:
    def emit(self, task_id: str, kind: str, data: dict[str, Any]) -> None:
        return None


class TaskEventAdapter:
    """Adapt Rock runtime event callbacks to the persistent event sink."""

    def __init__(self, sink: EventSink, task_id: str) -> None:
        self.sink = sink
        self.task_id = task_id

    def __call__(
        self,
        kind: str,
        name: str,
        status: str,
        detail: str,
        error: str | None = None,
    ) -> None:
        self.sink.emit(
            self.task_id,
            f"{kind}.{status}",
            {"name": name, "detail": detail, "error": error},
        )
