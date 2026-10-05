"""Verify release validation rejects incomplete archives and broken installations."""

from __future__ import annotations

import io
import subprocess
import tarfile
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest

from tools import check_artifacts

if TYPE_CHECKING:
    from pathlib import Path

PROJECT = {"name": "terminaltexteffects", "version": "0.15.0", "requires-python": ">=3.9"}
RUNTIME = "terminaltexteffects/__init__.py"
METADATA = b"Name: terminaltexteffects\nVersion: 0.15.0\nRequires-Python: >=3.9\n"


def make_artifact(tmp_path: Path, kind: str, files: dict[str, bytes]) -> Path:
    """Create a synthetic release archive without invoking a build backend."""
    path = tmp_path / f"example.{kind}"
    if kind == "whl":
        with ZipFile(path, "w") as archive:
            for name, content in files.items():
                archive.writestr(name, content)
    else:
        with tarfile.open(path, "w:gz") as archive:
            for name, content in files.items():
                member = tarfile.TarInfo(f"example/{name}")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
    return path


@pytest.mark.parametrize("kind", ["whl", "tar.gz"])
@pytest.mark.parametrize("fault", ["none", "runtime", "metadata", "version", "python", "development", "legacy"])
def test_archive_inventory_and_metadata(tmp_path: Path, kind: str, fault: str) -> None:
    """Both archive formats reject omitted runtime files and incorrect required metadata."""
    metadata_name = "example.dist-info/METADATA" if kind == "whl" else "PKG-INFO"
    files = {RUNTIME: b"", metadata_name: METADATA}
    if fault == "runtime":
        del files[RUNTIME]
    elif fault == "metadata":
        del files[metadata_name]
    elif fault == "version":
        files[metadata_name] = METADATA.replace(b"0.15.0", b"0.14.0")
    elif fault == "python":
        files[metadata_name] = METADATA.replace(b">=3.9", b">=3.10")
    if fault == "development":
        files["dev_effects/arbitrary_prototype.py"] = b""
    elif fault == "legacy":
        files["terminaltexteffects/effects/effect_dev.py"] = b""
    artifact = make_artifact(tmp_path, kind, files)
    if fault == "none":
        check_artifacts.validate_artifact(artifact, {RUNTIME}, PROJECT)
    else:
        pattern = {
            "development": "Development files",
            "legacy": "Development files",
            "runtime": "Missing runtime",
            "metadata": "Expected one",
            "version": "Version",
            "python": "Requires-Python",
        }
        with pytest.raises(ValueError, match=pattern[fault]):
            check_artifacts.validate_artifact(artifact, {RUNTIME}, PROJECT)


@pytest.mark.parametrize("count", [0, 1, 2])
def test_single_artifact_rejects_missing_or_ambiguous_builds(tmp_path: Path, count: int) -> None:
    """Never silently choose a stale wheel or accept a build that produced nothing."""
    for index in range(count):
        (tmp_path / f"example-{index}.whl").touch()
    if count == 1:
        assert check_artifacts.single_artifact(tmp_path, "*.whl").name == "example-0.whl"
    else:
        with pytest.raises(ValueError, match="Expected exactly one"):
            check_artifacts.single_artifact(tmp_path, "*.whl")


def test_run_isolates_environment_and_propagates_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Checkout import overrides are removed, and failed subprocesses fail validation."""
    monkeypatch.setenv("PYTHONPATH", "/checkout")
    monkeypatch.setenv("PYTHONHOME", "/checkout")
    monkeypatch.setenv("TTE_DEV_EFFECTS_DIR", "/checkout/dev_effects")

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["cwd"] == tmp_path
        environment = kwargs["env"]
        assert isinstance(environment, dict)
        assert "PYTHONPATH" not in environment
        assert "PYTHONHOME" not in environment
        assert "TTE_DEV_EFFECTS_DIR" not in environment
        assert environment["XDG_CONFIG_HOME"] == str(tmp_path / ".empty-config")
        return subprocess.CompletedProcess(command, 1, "", "broken build")

    monkeypatch.setattr(check_artifacts.subprocess, "run", fake_run)
    with pytest.raises(subprocess.CalledProcessError):
        check_artifacts.run(["uv", "build"], tmp_path)


@pytest.mark.parametrize("fault", ["none", "help", "render"])
def test_smoke_checks_both_commands_outside_checkout(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
) -> None:
    """Clean installs exercise both entry points and reject missing effects or output."""
    calls: list[list[str]] = []

    def fake_run(command: list[str], cwd: Path, *, input_text: str | None = None) -> str:
        assert cwd == tmp_path / "outside-checkout"
        calls.append(command)
        if command[-1] == "--help":
            return "no effects" if fault == "help" else "wipe"
        if input_text is not None:
            assert input_text == "OK"
            return "empty" if fault == "render" else "OK"
        return ""

    monkeypatch.setattr(check_artifacts, "run", fake_run)
    wheel = tmp_path / "example.whl"
    if fault == "none":
        check_artifacts.smoke_install(wheel, tmp_path, "clean")
        assert len(calls) == 7
        assert calls[2][1:3] == ["-I", "-c"]
        assert str(wheel) in calls[1]
        assert calls[3][0].endswith(("tte", "tte.exe"))
        assert calls[5][0].endswith(("terminaltexteffects", "terminaltexteffects.exe"))
    else:
        with pytest.raises(ValueError, match="did not"):
            check_artifacts.smoke_install(wheel, tmp_path, "clean")
