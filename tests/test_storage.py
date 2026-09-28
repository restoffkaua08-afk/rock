from rock.core.contracts import Task
from rock.storage.sqlite import SQLiteStore


def test_sqlite_store(tmp_path) -> None:
    store = SQLiteStore(str(tmp_path / "rock.db"))
    store.save_task(Task(id="t1", prompt="hello"))
    assert (tmp_path / "rock.db").exists()
