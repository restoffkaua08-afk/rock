from typer.testing import CliRunner

from rock.cli.main import app


runner = CliRunner()


def test_root_prompt_uses_mock_council(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ROCK_MODE", "mock")
    monkeypatch.setenv("ROCK_DB_PATH", str(tmp_path / "sessions.db"))

    result = runner.invoke(app, ["Explain Git briefly"])

    assert result.exit_code == 0, result.output
    assert "Mock synthesis" in result.output
    assert "Processo concluído" in result.output
    assert (tmp_path / "sessions.db").exists()


def test_run_command_uses_mock_council(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("ROCK_MODE", "mock")
    monkeypatch.setenv("ROCK_DB_PATH", str(tmp_path / "sessions.db"))

    result = runner.invoke(app, ["run", "What is REST?"])

    assert result.exit_code == 0, result.output
    assert "Mock synthesis" in result.output
    assert "Processo concluído" in result.output


def test_doctor_does_not_run_live_checks_by_default(monkeypatch) -> None:
    monkeypatch.setenv("ROCK_MODE", "live")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    assert "Live provider checks disabled" in result.output


def test_doctor_check_uses_provider_health(monkeypatch) -> None:
    monkeypatch.setenv("ROCK_MODE", "live")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    async def fake_health(self, model, *, timeout=10):
        return True

    monkeypatch.setattr("rock.core.providers.Provider.health_check", fake_health)
    result = runner.invoke(app, ["doctor", "--check"])
    assert result.exit_code == 0, result.output
    assert "OpenAI: reachable" in result.output
