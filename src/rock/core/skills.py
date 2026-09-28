# ruff: isort: skip_file
from __future__ import annotations

import os
import re
from pathlib import Path

from rock.config.settings import get_settings
from rock.core.contracts import Capability, Skill


class SkillRegistry:
    """Discover and safely load instruction-only skills.

    A skill is data/instructions in V0.4. It does not execute tools by itself.
    """

    def __init__(self, roots: list[str | Path] | None = None) -> None:
        self.roots = [Path(r).expanduser().resolve() for r in (roots or [])]
        self.skills: dict[str, Skill] = {}

    def discover(self) -> dict[str, Skill]:
        self.skills.clear()
        for root in self.roots:
            if not root.is_dir():
                continue
            for path in root.rglob("SKILL.md"):
                try:
                    resolved = path.resolve()
                    resolved.relative_to(root)
                    text = resolved.read_text(encoding="utf-8", errors="replace")
                except (OSError, ValueError):
                    continue
                skill = self._parse(resolved, text, root)
                self.skills[skill.id] = skill
        return self.skills

    @classmethod
    def _parse(cls, path: Path, text: str, root: Path) -> Skill:
        metadata: dict[str, str] = {}
        body = text
        if text.startswith("---\n"):
            parts = text.split("\n---\n", 1)
            if len(parts) == 2:
                raw, body = parts
                for line in raw.splitlines()[1:]:
                    if ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    metadata[key.strip().lower()] = value.strip().strip('"').strip("'")

        name = metadata.get("name") or path.parent.name
        description = metadata.get("description", "")
        return Skill(
            id=cls._id_for(path),
            name=name,
            description=description,
            instructions=body.strip(),
            source=str(root),
        )

    @staticmethod
    def _id_for(path: Path) -> str:
        raw = path.parent.name.lower().strip()
        return re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-") or "skill"

    def get(self, skill_id: str) -> Skill | None:
        return self.skills.get(skill_id)

    def select(self, skill_ids: list[str]) -> list[Skill]:
        return [self.skills[item] for item in skill_ids if item in self.skills]


def default_skill_roots() -> list[Path]:
    roots = [Path(__file__).resolve().parents[2] / "skills"]
    configured = get_settings().rock_superpowers_path or os.getenv("ROCK_SUPERPOWERS_PATH")
    if configured:
        roots.append(Path(configured).expanduser())
    return roots
