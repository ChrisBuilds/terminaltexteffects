"""Verify local QA scope, preview safety and failure propagation."""

from __future__ import annotations

import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from tools import qa

if TYPE_CHECKING:
    from pathlib import Path


def test_selection_includes_all_work_states(tmp_path: Path) -> None:
    """Real Git selection preserves deletions, both rename paths and unusual filenames."""

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603,S607

    git("init")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    for name in ("old.py", "deleted.py", "unstaged.py"):
        (tmp_path / name).write_text("original\n")
    git("add", ".")
    git("commit", "-m", "base")
    git("tag", "base")
    (tmp_path / "committed.py").write_text("committed\n")
    git("add", ".")
    git("commit", "-m", "branch")
    git("mv", "old.py", "renamed.py")
    (tmp_path / "deleted.py").unlink()
    (tmp_path / "unstaged.py").write_text("changed\n")
    (tmp_path / "space name.py").write_text("new\n")
    (tmp_path / ".gitignore").write_text("ignored.py\n")
    (tmp_path / "ignored.py").write_text("ignored\n")
    assert qa.changed_files(tmp_path, "base") == [
        ".gitignore",
        "committed.py",
        "deleted.py",
        "old.py",
        "renamed.py",
        "space name.py",
        "unstaged.py",
    ]


def test_selection_includes_staged_path_when_worktree_cancels_change(tmp_path: Path) -> None:
    """A staged diff remains selected when unstaged edits restore the HEAD contents."""

    def git(*args: str) -> bytes:
        return subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True).stdout  # noqa: S603,S607

    git("init")
    git("config", "user.email", "test@example.invalid")
    git("config", "user.name", "Test")
    target = tmp_path / "docs.md"
    target.write_text("original\n")
    git("add", "docs.md")
    git("commit", "-m", "base")
    git("tag", "base")
    target.write_text("staged version\n")
    git("add", "docs.md")
    target.write_text("original\n")

    assert git("status", "--short").decode().strip() == "MM docs.md"
    assert qa.changed_files(tmp_path, "base") == ["docs.md"]


def test_deleted_workflow_still_triggers_validation(tmp_path: Path) -> None:
    """Removed inputs affect selection without being passed to Python file checks."""
    commands = qa.plan(tmp_path, [".github/workflows/deleted.yml", "gone.py"], [], None)
    assert any("tools/check_workflows.py" in command for _, command in commands)
    assert not any("ruff" in command for _, command in commands)
    assert not any("pytest" in command for _, command in commands)


def test_focused_nodes_and_keywords_are_literal(tmp_path: Path) -> None:
    """Shell characters and parametrized nodes remain separate arguments."""
    commands = qa.plan(tmp_path, [], ["tests/test_file.py::test_case[a b]"], "value or other")
    assert commands == [
        (
            "Explicit focused tests",
            [sys.executable, "-m", "pytest", "./tests/test_file.py::test_case[a b]", "-k", "value or other"],
        )
    ]


def test_docs_select_strict_build_without_tests(tmp_path: Path) -> None:
    """Prose checks preserve the documentation build and never infer pytest."""
    commands = qa.plan(tmp_path, ["docs/development.md"], [], None)
    assert any("mkdocs" in command and "--strict" in command for _, command in commands)
    assert not any("pytest" in command for _, command in commands)


@pytest.mark.parametrize(
    "args", [["-k", "foo"], ["--test", "tests"], ["--test", "../tests/test_local_qa.py"], ["--test", "--all"]]
)
def test_rejects_unfocused_or_invalid_test_selection(args: list[str]) -> None:
    """Directories and options cannot broaden the intended focused test scope."""
    with pytest.raises(SystemExit) as error:
        qa.main(args)
    assert error.value.code == 2


def test_dry_run_executes_no_checks(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Preview reports skipped tests without invoking checks or hygiene."""
    monkeypatch.setattr(qa, "changed_files", lambda *_: ["docs/development.md"])

    def unexpected(*_args: object, **_kwargs: object) -> None:
        pytest.fail("dry run executed a check")

    monkeypatch.setattr(qa, "check_hygiene", unexpected)
    monkeypatch.setattr(qa.subprocess, "run", unexpected)
    assert qa.main(["--dry-run"]) == 0
    assert "Tests NOT RUN" in capsys.readouterr().out


def test_failure_status_propagates_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """The first failing tool stops execution with its original status."""
    monkeypatch.setattr(qa, "changed_files", lambda *_: ["docs/development.md"])
    monkeypatch.setattr(qa, "check_hygiene", lambda _: 0)
    calls: list[list[str]] = []

    def failed(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 7)

    monkeypatch.setattr(qa.subprocess, "run", failed)
    assert qa.main([]) == 7
    assert len(calls) == 1
