from pathlib import Path


def test_portable_layout_has_required_scripts() -> None:
    root = Path(__file__).parents[1]
    for name in ("setup.ps1", "rock.ps1", "update.ps1", "install-path.ps1"):
        assert (root / "scripts" / name).exists()


def test_portable_setup_documents_local_env_and_database() -> None:
    root = Path(__file__).parents[1]
    text = (root / "docs" / "PORTABLE_WINDOWS.md").read_text(encoding="utf-8")
    assert ".env" in text
    assert ".rock/" in text
    assert "scripts\\setup.ps1" in text
