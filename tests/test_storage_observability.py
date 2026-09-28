from rock.core.contracts import Artifact, Execution, ExecutionStatus, Task, Verification
from rock.observability.events import SQLiteEventSink
from rock.storage.sqlite import SQLiteStore


def test_sqlite_persists_execution_artifact_verification_and_events(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / "rock.db"))
    task = Task(id="t1", prompt="hello")
    execution = Execution(
        id="e1",
        task_id=task.id,
        actor="agent",
        action="demo",
        status=ExecutionStatus.SUCCESS,
    )
    artifact = Artifact(
        id="a1",
        type="text",
        content="result",
        source="test",
        task_id=task.id,
    )
    verification = Verification(
        target="e1",
        verifier="test",
        checks=["status"],
        passed=True,
    )

    store.save_task(task)
    store.save_execution(execution)
    store.save_artifact(artifact)
    store.save_verification(verification)
    SQLiteEventSink(store).emit(task.id, "tool.completed", {"execution_id": "e1"})

    events = store.list_events(task.id)
    assert events[0]["kind"] == "tool.completed"
    assert events[0]["data"]["execution_id"] == "e1"
