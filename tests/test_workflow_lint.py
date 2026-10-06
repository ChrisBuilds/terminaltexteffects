"""Exercise workflow discovery, required tooling, and real actionlint/ShellCheck diagnostics."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from tools import check_workflows

if TYPE_CHECKING:
    from pathlib import Path


def test_tracked_workflow_selection(tmp_path: Path) -> None:
    """Include YAML/rename destinations and exclude deleted, untracked, and unrelated files."""

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)  # noqa: S603, S607

    git("init")
    folder = tmp_path / ".github/workflows"
    folder.mkdir(parents=True)
    for name in ("ci.yml", "pages.yaml", "deleted.yml", "README.md"):
        (folder / name).write_text("placeholder\n")
    git("add", ".")
    git("mv", ".github/workflows/ci.yml", ".github/workflows/renamed.yml")
    (folder / "deleted.yml").unlink()
    (folder / "scratch.yml").write_text("untracked\n")
    assert check_workflows.workflow_files(tmp_path) == [
        ".github/workflows/pages.yaml",
        ".github/workflows/renamed.yml",
    ]


@pytest.mark.parametrize("tool", ["TTE_ACTIONLINT", "TTE_SHELLCHECK"])
def test_missing_tool_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tool: str
) -> None:
    """An explicit missing tool fails instead of silently skipping checks or using another version."""
    monkeypatch.setattr(check_workflows.shutil, "which", lambda value: None if value == "absent" else value)
    monkeypatch.setenv(tool, "absent")
    assert check_workflows.check(["ci.yml"], tmp_path) == 1
    assert "Missing " + tool.removeprefix("TTE_").lower() in capsys.readouterr().err


@pytest.fixture
def workflow_tools() -> None:
    """Run real tool fixtures in Code quality; other matrix jobs need no extra tool installation."""
    available = all(
        shutil.which(os.environ.get(key, default))
        for key, default in (
            ("TTE_ACTIONLINT", "actionlint"),
            ("TTE_SHELLCHECK", "shellcheck"),
        )
    )
    if not available:
        if os.environ.get("TTE_REQUIRE_ACTIONLINT") == "1":
            pytest.fail("Code quality requires actionlint and ShellCheck integration fixtures")
        pytest.skip("Install actionlint and ShellCheck to exercise workflow integration")


@pytest.mark.usefixtures("workflow_tools")
@pytest.mark.parametrize(
    ("extra", "script", "expected"),
    [
        ("", 'echo "ok"', None),
        ("    if: ${{ github.nonexistent }}\n", 'echo "ok"', "property"),
        ("    needs: missing_job\n", 'echo "ok"', "missing_job"),
        ("", 'value="hello world"; echo $value', "SC2086"),
    ],
    ids=["valid", "invalid-expression", "missing-job", "unquoted-shell-value"],
)
def test_real_workflow_diagnostics(
    tmp_path: Path, extra: str, script: str, expected: str | None, capfd: pytest.CaptureFixture[str]
) -> None:
    """Reject meaningful workflow and embedded shell errors while leaving inputs unchanged."""
    workflow = tmp_path / "fixture.yaml"
    text = (
        f"name: Fixture\non: push\njobs:\n  verify:\n{extra}"
        f"    runs-on: ubuntu-24.04\n    steps:\n      - run: {script}\n"
    )
    workflow.write_text(text)
    status = check_workflows.check([str(workflow)], tmp_path)
    output = capfd.readouterr()
    if expected is None:
        assert status == 0, output
    else:
        assert status != 0
        assert expected in output.out + output.err
    assert workflow.read_text() == text


def test_wrong_version_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """An installed but different actionlint version must not validate workflows."""
    monkeypatch.setattr(check_workflows.shutil, "which", lambda value: value)
    calls: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="0.0.0\n")

    monkeypatch.setattr(check_workflows.subprocess, "run", run)
    assert check_workflows.check(["fixture.yml"], tmp_path) == 1
    assert check_workflows.ACTIONLINT_VERSION in capsys.readouterr().err
    assert len(calls) == 1
    assert calls[0][-1] == "-version"
