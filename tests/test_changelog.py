"""Verify fragment validation, read-only previews, and history-preserving release assembly."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools import generate_changelog


@pytest.fixture
def changelog_project(tmp_path: Path) -> Path:
    """Create a disposable project with the production Towncrier config and template."""
    root = Path(__file__).resolve().parents[1]
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    shutil.copyfile(root / "pyproject.toml", tmp_path / "pyproject.toml")
    shutil.copyfile(root / "changelog.d" / "template.md.jinja", fragments / "template.md.jinja")
    (tmp_path / "CHANGELOG.md").write_text(
        f"# Changelog\n\n{generate_changelog.PREVIEW_START}\n\n"
        f"{generate_changelog.EMPTY_PREVIEW}\n\n{generate_changelog.PREVIEW_END}\n\n"
        "<!-- towncrier release notes start -->\n\n## 0.15.0\n\nOriginal published history.\n",
        encoding="utf-8",
    )
    return tmp_path


def initialize_git(root: Path) -> None:
    """Commit a baseline in a disposable repository."""
    for args in (
        ("init", "-b", "main"),
        ("config", "user.email", "test@example.com"),
        ("config", "user.name", "Changelog Test"),
        ("add", "."),
        ("commit", "-m", "Initial changelog"),
    ):
        generate_changelog.git_output(root, *args)


def commit_changes(root: Path) -> None:
    """Commit the current test branch changes."""
    generate_changelog.git_output(root, "add", ".")
    generate_changelog.git_output(root, "commit", "-m", "Update branch")


def test_preview_edit_alone_does_not_bypass_fragment_requirement(changelog_project: Path) -> None:
    """Editing the canonical changelog cannot replace a note or explicit skip reason."""
    initialize_git(changelog_project)
    generate_changelog.git_output(changelog_project, "checkout", "-b", "feature")
    path = changelog_project / "CHANGELOG.md"
    path.write_text(path.read_text(encoding="utf-8") + "\nA header edit.\n", encoding="utf-8")
    commit_changes(changelog_project)
    with pytest.raises(ValueError, match="preview edits alone"):
        generate_changelog.validate_decision(changelog_project, "main")


def test_skip_fragment_satisfies_branch_decision(changelog_project: Path) -> None:
    """An internal-only branch records its exemption in a real issue-numbered fragment."""
    initialize_git(changelog_project)
    generate_changelog.git_output(changelog_project, "checkout", "-b", "feature")
    (changelog_project / "changelog.d" / "123.skip.md").write_text("Internal tooling only.\n", encoding="utf-8")
    commit_changes(changelog_project)
    generate_changelog.validate_decision(changelog_project, "main")


@pytest.mark.parametrize("name", ["0.fixed.md", "123.typo.md", "not-an-issue.fixed.md"])
def test_invalid_fragment_names_are_rejected(tmp_path: Path, name: str) -> None:
    """Unknown categories and invalid issue identifiers cannot silently disappear from releases."""
    (tmp_path / name).write_text("A note.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid changelog fragment"):
        generate_changelog.validate_fragments(tmp_path)


def test_empty_skip_reason_is_rejected(tmp_path: Path) -> None:
    """A skip fragment must explain why no user-facing note is needed."""
    (tmp_path / "123.skip.md").write_text(" \n", encoding="utf-8")
    with pytest.raises(ValueError, match="Empty changelog fragment or skip reason"):
        generate_changelog.validate_fragments(tmp_path)


def test_render_preview_orders_categories_and_hides_skip_reasons(changelog_project: Path) -> None:
    """Real Towncrier output has issue links, useful categories, and no internal-only reasons."""
    fragments = changelog_project / "changelog.d"
    (fragments / "123.fixed.md").write_text("Corrected rendering.\n", encoding="utf-8")
    (fragments / "124.breaking.md").write_text("Requires Python 3.9.\n", encoding="utf-8")
    (fragments / "125.skip.md").write_text("Internal cleanup only.\n", encoding="utf-8")
    before = {path.name: path.read_bytes() for path in fragments.iterdir()}
    preview = generate_changelog.render_preview(changelog_project)
    assert preview.startswith("## Unreleased\n\n### Breaking changes\n\n")
    assert preview.index("### Breaking changes") < preview.index("### Fixed")
    assert "[#123](https://github.com/ChrisBuilds/terminaltexteffects/issues/123)" in preview
    assert "Internal cleanup" not in preview
    assert "### Added" not in preview
    assert {path.name: path.read_bytes() for path in fragments.iterdir()} == before


def test_skip_only_preview_has_no_user_facing_changes(changelog_project: Path) -> None:
    """A release with only internal changes has no empty categories or skip-note output."""
    (changelog_project / "changelog.d" / "123.skip.md").write_text("Only CI changed.\n", encoding="utf-8")
    assert generate_changelog.render_preview(changelog_project) == generate_changelog.EMPTY_PREVIEW


@pytest.mark.parametrize(
    "text",
    [
        "No markers",
        f"{generate_changelog.PREVIEW_END}\n{generate_changelog.PREVIEW_START}",
        f"{generate_changelog.PREVIEW_START}\n{generate_changelog.PREVIEW_START}\n{generate_changelog.PREVIEW_END}",
    ],
)
def test_preview_replacement_rejects_ambiguous_markers(text: str) -> None:
    """Missing, duplicate, or inverted markers cannot cause loss of published history."""
    with pytest.raises(ValueError, match="preview"):
        generate_changelog.replace_preview(text, "New notes")


def test_check_reports_staleness_without_writing(changelog_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CI reports stale previews, leaves files unchanged, and accepts a refreshed preview."""
    (changelog_project / "changelog.d" / "123.added.md").write_text("A new option.\n", encoding="utf-8")
    monkeypatch.setattr(generate_changelog, "__file__", str(changelog_project / "tools" / "generate_changelog.py"))
    monkeypatch.setattr(sys, "argv", ["generate_changelog.py", "--check"])
    path = changelog_project / "CHANGELOG.md"
    original = path.read_bytes()
    assert generate_changelog.main() == 1
    assert path.read_bytes() == original
    path.write_text(
        generate_changelog.replace_preview(
            path.read_text(encoding="utf-8"), generate_changelog.render_preview(changelog_project)
        ),
        encoding="utf-8",
    )
    assert generate_changelog.main() == 0


def test_release_assembly_preserves_history_and_consumes_fragments(changelog_project: Path) -> None:
    """The documented release process assembles dated notes while preserving published entries."""
    fragments = changelog_project / "changelog.d"
    (fragments / "123.fixed.md").write_text("Corrected rendering.\n", encoding="utf-8")
    (fragments / "124.skip.md").write_text("Internal cleanup.\n", encoding="utf-8")
    initialize_git(changelog_project)
    generate_changelog.git_output(changelog_project, "checkout", "-b", "release")
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
    assert not (fragments / "123.fixed.md").exists()
    assert not (fragments / "124.skip.md").exists()
    assert "Internal cleanup" not in path.read_text(encoding="utf-8")
    assert generate_changelog.render_preview(changelog_project) == generate_changelog.EMPTY_PREVIEW
    commit_changes(changelog_project)
    generate_changelog.validate_decision(changelog_project, "main")
