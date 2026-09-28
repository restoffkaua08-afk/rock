# ruff: isort: skip_file
from __future__ import annotations

import os
from pathlib import Path

from rock.config.settings import get_settings
from rock.core.contracts import Skill


class SkillRegistry:
    def __init__(self, roots: list[str | Path] | None = None) -> None:
        self.roots = [Path(r).expanduser() for r in (roots or [])]
        self.skills: dict[str, Skill] = {}

    def discover(self) -> dict[str, Skill]:
        self.skills.clear()
        for root in self.roots:
            if not root.exists():
                continue
            for path in root.rglob("SKILL.md"):
                skill_id = self._id_for(path)
                text = path.read_text(encoding="utf-8", errors="replace")
                self.skills[skill_id] = Skill(
                    id=skill_id,
                    name=path.parent.name,
                    description=f"Skill loaded from {path}",
                    instructions=text,
                    source=str(root),
                )
        return self.skills

    @staticmethod
    def _id_for(path: Path) -> str:
        return path.parent.name.lower().replace(" ", "-")

    def get(self, skill_id: str) -> Skill | None:
        return self.skills.get(skill_id)


def default_skill_roots() -> list[Path]:
    roots = [Path(__file__).resolve().parents[2] / "skills"]
    configured = get_settings().rock_superpowers_path or os.getenv("ROCK_SUPERPOWERS_PATH")
    if configured:
        roots.append(Path(configured).expanduser())
    return roots
