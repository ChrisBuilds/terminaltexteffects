"""Verify fragment validation, the changelog decision, previews, and release assembly."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import changelog


@pytest.fixture
def changelog_project(tmp_path: Path) -> Path:
    """Create a disposable project with the production Towncrier config and template."""
    root = Path(__file__).resolve().parents[1]
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    shutil.copyfile(root / "pyproject.toml", tmp_path / "pyproject.toml")
    shutil.copyfile(root / "changelog.d" / "template.md.jinja", fragments / "template.md.jinja")
    (tmp_path / "CHANGELOG.md").write_text(
        f"# Changelog\n\n{changelog.RELEASE_START}\n\n## 0.15.0\n\nOriginal published history.\n",
        encoding="utf-8",
    )
    return tmp_path


def initialize_git(root: Path) -> None:
    """Commit a baseline in a disposable repository and start a feature branch."""
    for args in (
        ("init", "-b", "main"),
        ("config", "user.email", "test@example.com"),
        ("config", "user.name", "Changelog Test"),
        ("add", "."),
        ("commit", "-m", "Initial changelog"),
        ("checkout", "-b", "feature"),
    ):
        changelog.git_output(root, *args)


def commit_changes(root: Path) -> None:
    """Commit the current test branch changes."""
    changelog.git_output(root, "add", "-A")
    changelog.git_output(root, "commit", "-m", "Update branch")


def test_changelog_edit_alone_is_not_a_decision(changelog_project: Path) -> None:
    """Editing CHANGELOG.md without a fragment fails the decision check."""
    initialize_git(changelog_project)
    path = changelog_project / "CHANGELOG.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nA header edit.\n", encoding="utf-8")
    commit_changes(changelog_project)
    with pytest.raises(ValueError, match="no-changelog label"):
        changelog.validate_decision(changelog_project, "main")


@pytest.mark.parametrize("name", ["123.fixed.md", "456.added.1.md"])
def test_added_fragment_satisfies_decision(changelog_project: Path, name: str) -> None:
    """Issue- or PR-numbered fragments satisfy the decision check."""
    initialize_git(changelog_project)
    (changelog_project / "changelog.d" / name).write_text("A note.\n", encoding="utf-8")
    commit_changes(changelog_project)
    changelog.validate_decision(changelog_project, "main")


@pytest.mark.parametrize("name", ["0.fixed.md", "123.typo.md", "123.skip.md", "not-an-issue.fixed.md"])
def test_invalid_fragment_names_are_rejected(tmp_path: Path, name: str) -> None:
    """Unknown categories and invalid numbers cannot silently disappear from releases."""
    (tmp_path / name).write_text("A note.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid changelog fragment"):
        changelog.validate_fragments(tmp_path)


def test_empty_fragment_is_rejected(tmp_path: Path) -> None:
    """A fragment must contain a note."""
    (tmp_path / "123.fixed.md").write_text(" \n", encoding="utf-8")
    with pytest.raises(ValueError, match="Empty changelog fragment"):
        changelog.validate_fragments(tmp_path)


def test_render_preview_orders_categories_without_consuming(changelog_project: Path) -> None:
    """Towncrier output has issue links and ordered categories, and leaves fragments in place."""
    fragments = changelog_project / "changelog.d"
    (fragments / "123.fixed.md").write_text("Corrected rendering.\n", encoding="utf-8")
    (fragments / "124.breaking.md").write_text("Requires Python 3.9.\n", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in fragments.iterdir()}
    preview = changelog.render_preview(changelog_project)
    assert preview.startswith("## Unreleased\n\n### Breaking changes\n\n")
    assert preview.index("### Breaking changes") < preview.index("### Fixed")
    assert "[#123](https://github.com/ChrisBuilds/terminaltexteffects/issues/123)" in preview
    assert "### Added" not in preview
    assert {path.name: path.read_bytes() for path in fragments.iterdir()} == before


def test_empty_preview(changelog_project: Path) -> None:
    """With no fragments, the preview says there are no pending changes."""
    assert changelog.render_preview(changelog_project) == changelog.EMPTY_PREVIEW


def test_insert_preview_keeps_history() -> None:
    """The preview goes above published history, and ambiguous markers are rejected."""
    text = f"# Changelog\n\n{changelog.RELEASE_START}\n\n## 0.15.0\n"
    result = changelog.insert_preview(text, "## Unreleased\n\nNotes.")
    assert result.index("## Unreleased") < result.index("## 0.15.0")
    with pytest.raises(ValueError, match="exactly one"):
        changelog.insert_preview(text + changelog.RELEASE_START, "## Unreleased")


def test_release_assembly_preserves_history_and_satisfies_decision(changelog_project: Path) -> None:
    """Release assembly consumes fragments into a dated section, which satisfies the decision check."""
    (changelog_project / "changelog.d" / "123.fixed.md").write_text("Corrected rendering.\n", encoding="utf-8")
    initialize_git(changelog_project)
    path = changelog_project / "CHANGELOG.md"
    archive = path.read_bytes().split(b"## 0.15.0", 1)[1]
    subprocess.run(
        [sys.executable, "-m", "towncrier", "build", "--yes", "--version", "0.16.0", "--date", "2026-10-04"],
        cwd=changelog_project,
        check=True,
        capture_output=True,
    )
    assert "## 0.16.0 - 2026-10-04\n\n### Fixed" in path.read_text(encoding="utf-8")
    assert path.read_bytes().split(b"## 0.15.0", 1)[1] == archive
    assert not (changelog_project / "changelog.d" / "123.fixed.md").exists()
    assert changelog.render_preview(changelog_project) == changelog.EMPTY_PREVIEW
    commit_changes(changelog_project)
    changelog.validate_decision(changelog_project, "main")


def test_release_notes_extracts_one_dated_section() -> None:
    """GitHub release notes are the matching dated section only."""
    text = (
        f"# Changelog\n\n{changelog.RELEASE_START}\n\n## 0.16.0 - 2026-11-01\n\n### Fixed\n\n- A fix.\n\n"
        "## 0.15.0\n\nOld notes.\n"
    )
    assert changelog.release_notes(text, "0.16.0") == "### Fixed\n\n- A fix."
    with pytest.raises(ValueError, match=r"no dated section for 0\.17\.0"):
        changelog.release_notes(text, "0.17.0")
