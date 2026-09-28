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
