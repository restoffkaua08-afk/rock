from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from rock.core.contracts import Response, Session, Task, Verification


class SQLiteStore:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def _init(self) -> None:
        with self._connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "task_id TEXT NOT NULL, responses TEXT NOT NULL, synthesis TEXT NOT NULL, "
                "verification TEXT NOT NULL)"
            )

    def save_task(self, task: Task) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO tasks(id, data) VALUES (?, ?)",
                (task.id, task.model_dump_json()),
            )

    def save_session(self, session: Session) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO sessions(id, data) VALUES (?, ?)",
                (session.id, session.model_dump_json()),
            )

    def save_run(
        self, task_id: str, responses: list[Response], synthesis: str, verification: Verification
    ) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO runs(task_id, responses, synthesis, verification) VALUES (?, ?, ?, ?)",
                (
                    task_id,
                    json.dumps([r.model_dump(mode="json") for r in responses]),
                    synthesis,
                    verification.model_dump_json(),
                ),
            )
