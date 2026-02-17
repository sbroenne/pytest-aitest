"""Tests for core.skill module."""

from pathlib import Path

import pytest

from pytest_aitest.core.skill import Skill, SkillError, SkillMetadata


def test_skill_name_rejects_trailing_hyphen() -> None:
    """Name must not end with a hyphen per Agent Skills naming rules."""
    with pytest.raises(SkillError, match="Invalid skill name"):
        SkillMetadata(name="bad-name-", description="desc")


def test_skill_name_rejects_consecutive_hyphens() -> None:
    """Name must not contain consecutive hyphens per Agent Skills naming rules."""
    with pytest.raises(SkillError, match="Invalid skill name"):
        SkillMetadata(name="bad--name", description="desc")


def test_skill_name_must_match_directory_name(tmp_path: Path) -> None:
    """SKILL.md frontmatter name must match the containing directory name."""
    skill_dir = tmp_path / "correct-dir"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: wrong-dir\ndescription: test skill\n---\n\n# Test",
        encoding="utf-8",
    )

    with pytest.raises(SkillError, match="must match directory name"):
        Skill.from_path(skill_dir)
