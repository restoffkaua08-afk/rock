from typer.testing import CliRunner

from rock.cli.main import app
from rock.config.settings import get_settings
from rock.storage.sqlite import SQLiteStore


def test_cli_mock_run_persists_runtime_trace(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ROCK_MODE", "mock")
    monkeypatch.setenv("ROCK_DB_PATH", str(tmp_path / "rock.db"))
    get_settings.cache_clear()

    result = CliRunner().invoke(app, ["run", "test the complete runtime"])
    assert result.exit_code == 0, result.output

    store = SQLiteStore(str(tmp_path / "rock.db"))
    with store._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM verifications").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM events").fetchone()[0] > 0
        assert db.execute("SELECT COUNT(*) FROM provider_usage").fetchone()[0] > 0

    get_settings.cache_clear()
