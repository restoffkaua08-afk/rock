from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from rock.core.contracts import Artifact, Execution, Response, Session, Task, Verification


class SQLiteStore:
    """Durable local event/state store for Rock runs."""

    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        return db

    def _init(self) -> None:
        with self._connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS tasks (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
            db.execute(
                "CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "task_id TEXT NOT NULL, responses TEXT NOT NULL, synthesis TEXT NOT NULL, "
                "verification TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS executions (id TEXT PRIMARY KEY, task_id TEXT NOT NULL, data TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS artifacts (id TEXT PRIMARY KEY, task_id TEXT NOT NULL, data TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS verifications "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, target TEXT NOT NULL, data TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS events "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, "
                "kind TEXT NOT NULL, data TEXT NOT NULL, created_at TEXT NOT NULL)"
            )
            db.execute(
                "CREATE TABLE IF NOT EXISTS provider_usage "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL, "
                "provider TEXT NOT NULL, model TEXT NOT NULL, input_tokens INTEGER, "
                "output_tokens INTEGER, estimated_cost REAL, created_at TEXT NOT NULL)"
            )

    def save_task(self, task: Task) -> None:
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO tasks(id, data) VALUES (?, ?)", (task.id, task.model_dump_json()))

    def save_session(self, session: Session) -> None:
        with self._connect() as db:
            db.execute("INSERT OR REPLACE INTO sessions(id, data) VALUES (?, ?)", (session.id, session.model_dump_json()))

    def save_run(self, task_id: str, responses: list[Response], synthesis: str, verification: Verification) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO runs(task_id, responses, synthesis, verification) VALUES (?, ?, ?, ?)",
                (task_id, json.dumps([r.model_dump(mode="json") for r in responses]), synthesis, verification.model_dump_json()),
            )

    def save_execution(self, execution: Execution) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO executions(id, task_id, data) VALUES (?, ?, ?)",
                (execution.id, execution.task_id, execution.model_dump_json()),
            )

    def save_artifact(self, artifact: Artifact) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO artifacts(id, task_id, data) VALUES (?, ?, ?)",
                (artifact.id, artifact.task_id, artifact.model_dump_json()),
            )

    def save_verification(self, verification: Verification) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO verifications(target, data) VALUES (?, ?)",
                (verification.target, verification.model_dump_json()),
            )

    def save_event(self, task_id: str, kind: str, data: dict[str, Any], created_at: str) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO events(task_id, kind, data, created_at) VALUES (?, ?, ?, ?)",
                (task_id, kind, json.dumps(data), created_at),
            )

    def save_provider_usage(self, task_id: str, response: Response) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO provider_usage(task_id, provider, model, input_tokens, output_tokens, estimated_cost, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task_id, response.provider, response.model, response.input_tokens, response.output_tokens,
                 response.estimated_cost, response.model_dump(mode="json").get("timestamp", "")),
            )

    def list_events(self, task_id: str) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT kind, data, created_at FROM events WHERE task_id = ? ORDER BY id",
                (task_id,),
            ).fetchall()
        return [{"kind": row["kind"], "data": json.loads(row["data"]), "created_at": row["created_at"]} for row in rows]
