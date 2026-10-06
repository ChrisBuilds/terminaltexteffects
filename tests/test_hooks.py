"""Verify staged-file QA dispatch and real pre-commit behavior."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path
from typing import Literal

import pytest

from tools import generate_changelog, run_hook


@pytest.mark.parametrize("check", ["lint", "format", "types"])
def test_hook_empty_file_list_does_not_check_entire_project(check: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """No selected Python files means no invocation of project-wide checks."""

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Empty file selection must not run a tool.")

    monkeypatch.setattr(run_hook.subprocess, "run", unexpected)
    assert run_hook.main([check]) == 0


@pytest.mark.parametrize("check", ["lint", "format", "types"])
def test_hook_uses_current_environment_preserves_paths_and_propagates_failure(
    check: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Arguments remain separate, safe fixes are explicit, and failures block commits."""
    commands: list[list[str]] = []

    def capture(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert kwargs["check"] is False
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(run_hook.subprocess, "run", capture)
    assert run_hook.main([check, "--", "file with spaces.py", "--version.pyi"]) == 7
    command = commands[0]
    assert command[0] == sys.executable
    assert command[-2:] == ["./file with spaces.py", "./--version.pyi"]
    if check == "lint":
        assert "--fix" in command
        assert "--no-unsafe-fixes" in command
    if check == "types":
        assert command[command.index("--pythonpath") + 1] == sys.executable


@pytest.mark.parametrize("changed", [b"changelog.d/1.fixed.md\0", b"CHANGELOG.md\0", b"tools/example.py\0"])
def test_changelog_hook_detects_deleted_and_renamed_staged_inputs(
    changed: bytes,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing fragment can still trigger validation through the staged Git diff."""
    commands: list[list[str]] = []
    validated: list[Path] = []
    monkeypatch.setattr(run_hook, "validate_staged_changelog", lambda root: validated.append(root) or 0)

    def capture(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=changed)

    monkeypatch.setattr(run_hook.subprocess, "run", capture)
    assert run_hook.main(["changelog"]) == 0
    assert "--cached" in commands[0]
    assert "--no-renames" in commands[0]
    assert len(commands) == 1
    assert bool(validated) is not changed.startswith(b"tools/example.py")


@pytest.mark.skipif(
    any(find_spec(module) is None for module in ("pre_commit", "ruff", "pyright")),
    reason="Real hook integration runs in Code quality with locked development tools.",
)
@pytest.mark.parametrize("layout", ["separate", "overlapping"])
def test_pre_commit_fixes_require_restaging_and_preserve_unstaged_changes(
    tmp_path: Path,
    layout: Literal["separate", "overlapping"],
) -> None:
    """Exercise real staging isolation, a formatter fix, and a failing Pyright check."""
    root = Path(__file__).resolve().parents[1]
    environment = {**os.environ, "PRE_COMMIT_HOME": str(tmp_path / "cache")}

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 - Test commands have separated arguments.
            list(args),
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def git(*args: str) -> str:
        result = run("git", *args)
        assert result.returncode == 0, result.stderr
        return result.stdout

    git("init")
    (tmp_path / "tools").mkdir()
    shutil.copy(root / "tools/run_hook.py", tmp_path / "tools/run_hook.py")
    shutil.copy(root / ".pre-commit-config.yaml", tmp_path / ".pre-commit-config.yaml")
    (tmp_path / ".venv").symlink_to(Path(sys.executable).parent.parent, target_is_directory=True)
    # Isolate staging/formatting semantics from changes to Ruff's default rule selection.
    (tmp_path / "pyproject.toml").write_text(
        '[tool.ruff.lint]\nselect = ["F"]\n\n[tool.pyright]\npythonVersion = "3.9"\n',
        encoding="utf-8",
    )
    source = tmp_path / "example.py"
    tail = "" if layout == "overlapping" else "".join(f"value_{index}: int = {index}\n" for index in range(6))
    staged = "value: int=1\n" + tail
    unstaged = staged + "# Keep this unstaged comment.\n"
    source.write_text(staged, encoding="utf-8")
    git("add", "example.py", "tools/run_hook.py", ".pre-commit-config.yaml")
    source.write_text(unstaged, encoding="utf-8")
    result = run(sys.executable, "-m", "pre_commit", "run")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "files were modified by this hook" in result.stdout
    expected = unstaged if layout == "overlapping" else "value: int = 1\n" + tail + "# Keep this unstaged comment.\n"
    assert source.read_text(encoding="utf-8") == expected
    assert git("show", ":example.py") == staged
    assert run(sys.executable, "-m", "ruff", "format", "example.py", "tools/run_hook.py").returncode == 0
    git("add", "example.py", "tools/run_hook.py")
    result = run(sys.executable, "-m", "pre_commit", "run")
    assert result.returncode == 0, result.stdout + result.stderr
    source.write_text('value: int = "wrong type"\n', encoding="utf-8")
    git("add", "example.py")
    result = run(sys.executable, "-m", "pre_commit", "run", "pyright")
    assert result.returncode == 1, result.stdout + result.stderr
    assert "reportAssignmentType" in result.stdout


@pytest.fixture
def changelog_repository(tmp_path: Path) -> Path:
    """Create a real indexed changelog with the project's renderer and configuration."""
    root = Path(__file__).resolve().parents[1]
    (tmp_path / "tools").mkdir()
    for name in ("tools/run_hook.py", "tools/generate_changelog.py", "pyproject.toml"):
        shutil.copy(root / name, tmp_path / name)
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    shutil.copy(root / "changelog.d/template.md.jinja", fragments / "template.md.jinja")
    (fragments / "123.fixed.md").write_text("Baseline release note.\n", encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(
        f"# Changelog\n{generate_changelog.PREVIEW_START}\n{generate_changelog.PREVIEW_END}\n"
        f"{generate_changelog.RELEASE_START}\n## 0.15.0\nPublished history.\n",
        encoding="utf-8",
    )
    assert changelog_command(tmp_path, "generate_changelog.py").returncode == 0
    git_changelog(tmp_path, "init")
    git_changelog(tmp_path, "add", ".")
    git_changelog(
        tmp_path,
        "-c",
        "user.name=Hook Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "--no-verify",
        "-m",
        "Baseline",
    )
    (fragments / "124.skip.md").write_text("Internal tooling.\n", encoding="utf-8")
    git_changelog(tmp_path, "add", "changelog.d/124.skip.md")
    return tmp_path


def changelog_command(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run a real renderer or hook against the disposable repository."""
    return subprocess.run(  # noqa: S603 - Separated arguments; no shell.
        [sys.executable, str(root / "tools" / arguments[0]), *arguments[1:]],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )


def test_changelog_hook_ignores_untracked_invalid_fragments(changelog_repository: Path) -> None:
    """An untracked invalid note cannot block a valid indexed changelog."""
    fragment = changelog_repository / "changelog.d" / "not-a-fragment.txt"
    fragment.write_text("Unrelated draft", encoding="utf-8")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 0, result.stdout + result.stderr
    assert fragment.read_text(encoding="utf-8") == "Unrelated draft"


def git_changelog(root: Path, *arguments: str) -> str:
    """Inspect and update only the disposable repository's index."""
    return subprocess.run(  # noqa: S603 - Separated Git arguments without a shell.
        ["git", *arguments],  # noqa: S607 - Use the environment's Git binary.
        cwd=root,
        check=True,
        text=True,
        capture_output=True,
    ).stdout


def test_changelog_hook_rejects_preview_including_untracked_note(changelog_repository: Path) -> None:
    """A staged preview cannot pass by referring to a fragment absent from the index."""
    fragment = changelog_repository / "changelog.d/125.fixed.md"
    fragment.write_text("Uncommitted change.\n", encoding="utf-8")
    assert changelog_command(changelog_repository, "generate_changelog.py").returncode == 0
    git_changelog(changelog_repository, "add", "CHANGELOG.md")
    before = git_changelog(changelog_repository, "diff", "--cached")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 1
    assert "preview is stale" in result.stdout
    assert git_changelog(changelog_repository, "diff", "--cached") == before
    assert fragment.read_text(encoding="utf-8") == "Uncommitted change.\n"


def test_changelog_hook_uses_staged_fragment_preview_and_renderer(changelog_repository: Path) -> None:
    """Partial staging validates indexed content and preserves every unstaged edit."""
    fragment = changelog_repository / "changelog.d/125.fixed.md"
    fragment.write_text("Staged change.\n", encoding="utf-8")
    assert changelog_command(changelog_repository, "generate_changelog.py").returncode == 0
    git_changelog(changelog_repository, "add", "changelog.d/125.fixed.md", "CHANGELOG.md")
    fragment.write_text("", encoding="utf-8")
    preview = changelog_repository / "CHANGELOG.md"
    preview.write_text("Unstaged preview edit", encoding="utf-8")
    renderer = changelog_repository / "tools/generate_changelog.py"
    renderer.write_text('raise RuntimeError("Unstaged renderer")\n', encoding="utf-8")
    before = git_changelog(changelog_repository, "diff", "--cached")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 0, result.stdout + result.stderr
    assert fragment.read_text(encoding="utf-8") == ""
    assert preview.read_text(encoding="utf-8") == "Unstaged preview edit"
    assert "Unstaged renderer" in renderer.read_text(encoding="utf-8")
    assert git_changelog(changelog_repository, "diff", "--cached") == before


@pytest.mark.parametrize("fault", ["empty", "invalid-name"])
def test_changelog_hook_rejects_invalid_staged_fragment(changelog_repository: Path, fault: str) -> None:
    """Invalid index content fails even when working-directory content looks valid."""
    name = "125.fixed.md" if fault == "empty" else "invalid.md"
    fragment = changelog_repository / "changelog.d" / name
    fragment.write_text("" if fault == "empty" else "Invalid filename", encoding="utf-8")
    git_changelog(changelog_repository, "add", f"changelog.d/{name}")
    fragment.write_text("Valid unstaged content", encoding="utf-8")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode != 0
    assert ("Empty changelog" if fault == "empty" else "Invalid changelog fragment") in result.stderr
    assert fragment.read_text(encoding="utf-8") == "Valid unstaged content"


@pytest.mark.parametrize("operation", ["delete", "rename"])
def test_changelog_hook_respects_index_deletion_and_rename(changelog_repository: Path, operation: str) -> None:
    """Removed fragment paths stay absent from validation even if they reappear locally."""
    fragment = changelog_repository / "changelog.d/123.fixed.md"
    if operation == "delete":
        git_changelog(changelog_repository, "rm", "changelog.d/123.fixed.md")
    else:
        git_changelog(changelog_repository, "mv", "changelog.d/123.fixed.md", "changelog.d/126.fixed.md")
    assert changelog_command(changelog_repository, "generate_changelog.py").returncode == 0
    git_changelog(changelog_repository, "add", "CHANGELOG.md")
    fragment.write_text("", encoding="utf-8")
    before = git_changelog(changelog_repository, "diff", "--cached")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 0, result.stdout + result.stderr
    assert fragment.read_text(encoding="utf-8") == ""
    assert git_changelog(changelog_repository, "diff", "--cached") == before


@pytest.mark.skipif(find_spec("pre_commit") is None, reason="Real pre-commit integration runs in Code quality.")
def test_pre_commit_changelog_preserves_untracked_and_unstaged_files(changelog_repository: Path) -> None:
    """Exercise staged-only validation through pre-commit's real stash and restoration."""
    root = Path(__file__).resolve().parents[1]
    shutil.copy(root / ".pre-commit-config.yaml", changelog_repository / ".pre-commit-config.yaml")
    (changelog_repository / ".venv").symlink_to(Path(sys.executable).parent.parent, target_is_directory=True)
    git_changelog(changelog_repository, "add", ".pre-commit-config.yaml")
    untracked = changelog_repository / "changelog.d/unfinished.txt"
    untracked.write_text("Untracked draft", encoding="utf-8")
    tracked = changelog_repository / "changelog.d/123.fixed.md"
    tracked.write_text("", encoding="utf-8")
    before = git_changelog(changelog_repository, "diff", "--cached")
    result = subprocess.run(
        [sys.executable, "-m", "pre_commit", "run", "changelog"],
        cwd=changelog_repository,
        env={**os.environ, "PRE_COMMIT_HOME": str(changelog_repository / "cache")},
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert untracked.read_text(encoding="utf-8") == "Untracked draft"
    assert tracked.read_text(encoding="utf-8") == ""
    assert git_changelog(changelog_repository, "diff", "--cached") == before


def test_changelog_hook_materializes_sparse_index_files(changelog_repository: Path) -> None:
    """Changelog files outside a sparse checkout still participate in staged validation."""
    git_changelog(
        changelog_repository,
        "-c",
        "user.name=Hook Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "--no-verify",
        "-m",
        "Commit fixture inputs",
    )
    git_changelog(changelog_repository, "sparse-checkout", "set", "--cone", "tools")
    assert not (changelog_repository / "changelog.d").exists()
    config = changelog_repository / "pyproject.toml"
    config.write_text(config.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    git_changelog(changelog_repository, "add", "pyproject.toml")
    flags = git_changelog(changelog_repository, "ls-files", "-v")
    result = changelog_command(changelog_repository, "run_hook.py", "changelog")
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (changelog_repository / "changelog.d").exists()
    assert git_changelog(changelog_repository, "ls-files", "-v") == flags
