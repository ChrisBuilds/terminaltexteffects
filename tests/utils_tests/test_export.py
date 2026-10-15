"""Tests for converting recordings to GIF and WebP, without running external tools."""

from __future__ import annotations

import subprocess
import typing
from pathlib import Path

import pytest

from terminaltexteffects.engine._recording import RecordingHeader, RecordingWriter
from terminaltexteffects.utils import export

_GIF, _WEBP = export.FORMATS[1], export.FORMATS[2]


def _write_recording(path: Path) -> None:
    with RecordingWriter(path, RecordingHeader("test", 2, 1, 10)) as writer:
        writer.begin_segment("test")
        writer.write_frame("ab")
        writer.write_frame("cd")


def test_formats_follow_the_suffix() -> None:
    """The suffix should pick the format, and unknown suffixes should export a tterec."""
    assert export.format_for(Path("a.GIF")) is _GIF
    assert export.format_for(Path("a.webp")) is _WEBP
    assert export.format_for(Path("a.cast")) is export.FORMATS[0]


def test_missing_tools_are_named_with_their_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """A format whose commands are missing should say which and where to get them."""
    monkeypatch.setattr(export.shutil, "which", lambda name: None if name == "gif2webp" else f"/bin/{name}")
    assert export.format_problem(_GIF) is None
    assert export.format_problem(export.FORMATS[0]) is None
    assert export.format_problem(_WEBP) == "WebP needs gif2webp from libwebp on PATH."
    monkeypatch.setattr(export.shutil, "which", lambda _name: None)
    assert export.format_problem(_GIF) == "GIF needs agg 1.7 or later from github.com/asciinema/agg on PATH."


def test_agg_failure_names_the_minimum_version(monkeypatch: pytest.MonkeyPatch) -> None:
    """An agg that rejects an option, as releases before 1.7 reject `--quiet`, should say which version is needed."""
    monkeypatch.setattr(export.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(
        export.subprocess,
        "run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess([], 2, "", "error: Found argument '--quiet'"),
    )
    with pytest.raises(export.ExportError) as error:
        export._run(["agg", "--quiet"])
    assert str(error.value) == (
        "agg exited with 2: error: Found argument '--quiet'\n"
        "GIF and WebP need agg 1.7 or later; check it with: agg --version"
    )


def test_webp_export_renders_a_gif_with_agg_then_converts_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WebP output should render the canvas cast with agg and convert the GIF with gif2webp."""
    commands: list[list[str]] = []

    def run(command: list[str]) -> None:
        commands.append(command)
        if command[0] == "agg":
            assert Path(command[-2]).read_text(encoding="utf-8").startswith('{"version": 2')
        Path(command[-1]).write_bytes(command[0].encode())

    monkeypatch.setattr(export, "_run", run)
    monkeypatch.setattr(export.shutil, "which", lambda name: f"/bin/{name}")
    recording = tmp_path / "effect.tterec"
    _write_recording(recording)
    export.export_recording(recording, tmp_path / "out.webp", _WEBP, fps=30)
    assert [command[0] for command in commands] == ["agg", "gif2webp"]
    assert commands[0][commands[0].index("--fps-cap") + 1] == "31"
    assert commands[1][-3] == commands[0][-1]
    assert (tmp_path / "out.webp").read_bytes() == b"gif2webp"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["effect.tterec", "out.webp"]


@pytest.mark.parametrize(("gifsicle", "expected"), [(True, ["agg", "gifsicle"]), (False, ["agg"])])
def test_gif_export_uses_gifsicle_when_installed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gifsicle: bool,  # noqa: FBT001
    expected: list[str],
) -> None:
    """GIF output should be optimized with gifsicle when it is on PATH, and written straight from agg otherwise."""
    commands: list[list[str]] = []

    def run(command: list[str]) -> None:
        commands.append(command)
        Path(command[-1]).write_bytes(command[0].encode())

    monkeypatch.setattr(export, "_run", run)
    monkeypatch.setattr(export.shutil, "which", lambda name: f"/bin/{name}" if gifsicle or name != "gifsicle" else None)
    recording = tmp_path / "effect.tterec"
    _write_recording(recording)
    export.export_recording(recording, tmp_path / "out.gif", _GIF, fps=30)
    assert [command[0] for command in commands] == expected
    if gifsicle:
        assert commands[1][:2] == ["gifsicle", "-O3"]
        assert commands[1][2] == f"--lossy={export.GIFSICLE_LOSSY}"
        assert commands[1][3] == commands[0][-1]
    assert (tmp_path / "out.gif").read_bytes() == expected[-1].encode()


@pytest.mark.parametrize(("fps", "cap"), [(1, 2), (24, 25), (30, 31), (50, 51), (60, 51), (120, 51)])
def test_agg_fps_cap_is_one_above_the_frame_rate(fps: int, cap: int) -> None:
    """The cap should sit one above the frame rate, up to the fastest rate a GIF can play."""
    assert export.agg_fps_cap(fps) == cap


def test_failed_export_keeps_the_existing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A conversion that fails partway should leave the previous output untouched and no temporary file."""

    def run(command: list[str]) -> typing.NoReturn:
        Path(command[-1]).write_bytes(b"partial")
        message = f"{command[0]} exited with 1: broken"
        raise export.ExportError(message)

    monkeypatch.setattr(export, "_run", run)
    recording = tmp_path / "effect.tterec"
    _write_recording(recording)
    output = tmp_path / "out.gif"
    output.write_bytes(b"previous")
    with pytest.raises(export.ExportError, match="agg exited with 1"):
        export.export_recording(recording, output, _GIF, fps=30)
    assert output.read_bytes() == b"previous"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["effect.tterec", "out.gif"]
