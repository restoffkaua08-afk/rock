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
