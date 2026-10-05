"""Verify quality checks select branch changes safely and propagate tool failures."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from tools import check_quality

if TYPE_CHECKING:
    from pathlib import Path


def git(root: Path, *args: str) -> str:
    """Run Git against a disposable test repository."""
    return subprocess.run(  # noqa: S603 - Arguments are passed without a shell.
        ["git", *args],  # noqa: S607 - Use the environment's Git binary.
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    """Create committed Python files for diff selection tests."""
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Quality Test")
    for name in ("modified.py", "deleted.py", "renamed.py"):
        (tmp_path / name).write_text(f'# {name}\nVALUE = "original"\n')
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "Initial files")
    git(tmp_path, "checkout", "-b", "feature")
    return tmp_path


def test_changed_files_include_rename_destination_and_skip_deleted(repository: Path) -> None:
    """Added files and rename destinations survive selection; deleted and non-Python files do not."""
    (repository / "modified.py").write_text('VALUE = "changed"\n')
    (repository / "deleted.py").unlink()
    git(repository, "mv", "renamed.py", "renamed with spaces.py")
    (repository / "added.pyi").write_text("VALUE: str\n")
    (repository / "README.md").write_text("Documentation\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "Change files")
    assert set(check_quality.changed_python_files(repository, "main", "HEAD")) == {
        "./modified.py",
        "./renamed with spaces.py",
        "./added.pyi",
    }


def test_branch_diff_includes_earlier_commits_but_not_main_changes(repository: Path) -> None:
    """The merge-base diff checks earlier branch commits without claiming new base changes."""
    (repository / "first.py").write_text("VALUE = 1\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "First branch commit")
    (repository / "second.py").write_text("VALUE = 2\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "Second branch commit")
    git(repository, "checkout", "main")
    (repository / "main_only.py").write_text("VALUE = 3\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "Advance main")
    git(repository, "checkout", "feature")
    assert check_quality.changed_python_files(repository, "main", "HEAD") == ["./first.py", "./second.py"]


def test_documentation_only_diff_selects_no_python_files(repository: Path) -> None:
    """Documentation-only branches complete without accidentally checking the entire repository."""
    (repository / "README.md").write_text("Documentation\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "Document workflow")
    assert check_quality.changed_python_files(repository, "main", "HEAD") == []


def test_tracked_files_include_unchanged_code_but_not_local_experiments(repository: Path) -> None:
    """Whole-project checks include unchanged code and stubs without claiming local prototypes."""
    for name in ("-leading-dash.py", "stub with spaces.pyi", "README.md"):
        (repository / name).write_text("# tracked\n")
    (repository / ".gitignore").write_text("dev_effects/\n")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "Track quality inputs")
    (repository / "local.py").write_text("# untracked\n")
    (repository / "dev_effects").mkdir()
    (repository / "dev_effects" / "effect_dev.py").write_text("# ignored\n")
    (repository / "deleted.py").unlink()
    assert check_quality.tracked_python_files(repository) == [
        "./-leading-dash.py",
        "./modified.py",
        "./renamed.py",
        "./stub with spaces.pyi",
    ]


@pytest.mark.parametrize("failure_index", [0, 1, 2])
@pytest.mark.parametrize("mode", ["changed", "all"])
def test_quality_failure_stops_later_checks(monkeypatch: pytest.MonkeyPatch, failure_index: int, mode: str) -> None:
    """Any formatter, linter, or type-check failure reaches CI without running later tools."""
    commands: list[list[str]] = []

    def run(command: list[str], *, cwd: Path, check: bool) -> subprocess.CompletedProcess[bytes]:
        del cwd, check
        commands.append(command)
        return subprocess.CompletedProcess(command, 7 if len(commands) == failure_index + 1 else 0)

    args = ["--all"] if mode == "all" else ["--base", "main"]
    selector = "tracked_python_files" if mode == "all" else "changed_python_files"
    monkeypatch.setattr(check_quality.sys, "argv", ["check_quality.py", *args])
    monkeypatch.setattr(check_quality, selector, lambda *_args: ["./file with spaces.py"])
    monkeypatch.setattr(check_quality.subprocess, "run", run)
    assert check_quality.main() == 7
    assert len(commands) == failure_index + 1
    assert all(command[-1] == "./file with spaces.py" for command in commands)
    assert all("--fix" not in command for command in commands)
