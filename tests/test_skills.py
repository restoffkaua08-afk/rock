from pathlib import Path

from rock.core.skills import SkillRegistry


def test_skill_registry_reads_metadata_and_instructions(tmp_path: Path) -> None:
    skill_dir = tmp_path / "Demo Skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: Demo\ndescription: Example skill\n---\n\nUse this workflow.",
        encoding="utf-8",
    )

    registry = SkillRegistry([tmp_path])
    found = registry.discover()

    assert "demo-skill" in found
    assert found["demo-skill"].name == "Demo"
    assert found["demo-skill"].description == "Example skill"
    assert "Use this workflow." in found["demo-skill"].instructions


def test_skill_registry_selects_known_ids(tmp_path: Path) -> None:
    skill_dir = tmp_path / "one"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# One", encoding="utf-8")

    registry = SkillRegistry([tmp_path])
    registry.discover()

    assert [item.id for item in registry.select(["one", "missing"])] == ["one"]
