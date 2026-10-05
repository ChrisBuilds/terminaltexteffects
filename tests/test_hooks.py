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

from tools import run_hook


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

    def capture(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=changed)

    monkeypatch.setattr(run_hook.subprocess, "run", capture)
    assert run_hook.main(["changelog"]) == 0
    assert "--cached" in commands[0]
    assert "--no-renames" in commands[0]
    assert len(commands) == (1 if changed.startswith(b"tools/example.py") else 2)
    if len(commands) == 2:
        assert commands[1][-1] == "--check"
        assert "--base" not in commands[1]


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
    (tmp_path / "pyproject.toml").write_text('[tool.pyright]\npythonVersion = "3.9"\n', encoding="utf-8")
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
