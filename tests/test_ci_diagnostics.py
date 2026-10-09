"""Exercise real pytest failure reports and stalled-test dumps without running extra suites."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

import pytest

from tools import write_test_context

if TYPE_CHECKING:
    from pathlib import Path


def test_context_omits_unrelated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Metadata identifies the tested revision without exporting arbitrary environment values."""
    monkeypatch.setenv("GITHUB_SHA", "tested-revision")
    monkeypatch.setenv("DIAGNOSTICS_HEAD", "pr-revision")
    monkeypatch.setenv("DIAGNOSTICS_BASE", "base-revision")
    monkeypatch.setenv("PRIVATE_TEST_VALUE", "must-not-be-exported")
    monkeypatch.setenv("PYTHONPATH", "private-path")
    result = write_test_context.context()
    assert result["revision"] == "tested-revision"
    assert result["pr_head"] == "pr-revision"
    assert result["base"] == "base-revision"
    assert "must-not-be-exported" not in json.dumps(result)
    assert "private-path" not in json.dumps(result)


def test_context_missing_tools_are_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    """An absent package is recorded as unknown, rather than fabricated or crashing metadata."""

    def missing(_name: str) -> str:
        raise write_test_context.PackageNotFoundError

    monkeypatch.setattr(write_test_context, "version", missing)
    assert write_test_context.context()["packages"] == dict.fromkeys(
        ("pytest", "pytest-xdist", "pytest-cov", "coverage")
    )


def test_context_cli_creates_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The reporting command creates a readable standalone artifact without running pytest."""
    output = tmp_path / "reports/context.json"
    monkeypatch.setattr(sys, "argv", ["write_test_context", "--output", str(output)])
    write_test_context.main()
    assert json.loads(output.read_text())["python"]


@pytest.mark.parametrize(
    ("source", "status", "tag", "workers"),
    [
        ("def test_failure():\n    assert False, 'diagnostic-sentinel'\n", 1, "failure", None),
        ("raise RuntimeError('collection-sentinel')\n", 2, "error", None),
        ("def test_failure():\n    assert False, 'worker-sentinel'\n", 1, "failure", "1"),
    ],
)
def test_failed_pytest_retains_junit(tmp_path: Path, source: str, status: int, tag: str, workers: str | None) -> None:
    """JUnit survives assertion/collection failures and pytest retains its failing exit status."""
    (tmp_path / "test_probe.py").write_text(source)
    report = tmp_path / "reports/results.xml"
    env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": ""}
    command = [sys.executable, "-m", "pytest", "-q", "test_probe.py", f"--junitxml={report}", "-o", "junit_logging=no"]
    if workers:
        command.extend(["-p", "xdist.plugin", "-n", workers])
    result = subprocess.run(  # noqa: S603 - Fixed interpreter/pytest arguments, isolated synthetic test.
        command,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == status, result.stdout + result.stderr
    tree = ET.parse(report)  # noqa: S314 - Locally generated pytest report, no external XML.
    assert tree.findall(f".//{tag}")


@pytest.mark.parametrize("workers", [None, "1"])
def test_stalled_test_dumps_without_stopping(tmp_path: Path, workers: str | None) -> None:
    """The traceback timer diagnoses a slow test without turning it into a timeout failure."""
    (tmp_path / "test_probe.py").write_text("import time\ndef test_stall():\n    time.sleep(0.3)\n")
    env = {**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "PYTEST_ADDOPTS": ""}
    command = [sys.executable, "-m", "pytest", "-q", "test_probe.py", "-o", "faulthandler_timeout=0.05"]
    if workers:
        command.extend(["-p", "xdist.plugin", "-n", workers])
    result = subprocess.run(  # noqa: S603 - Fixed interpreter/pytest arguments, bounded synthetic stall.
        command,
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Timeout" in result.stderr
    assert "test_stall" in result.stderr
