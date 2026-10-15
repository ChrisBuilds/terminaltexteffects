"""Tests for converting recordings to GIF and WebP, without running external tools."""

from __future__ import annotations

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


def test_webp_export_renders_a_gif_with_agg_then_converts_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WebP output should render the canvas cast with agg and convert the GIF with gif2webp."""
    commands: list[list[str]] = []

    def run(command: list[str]) -> None:
        commands.append(command)
        if command[0] == "agg":
            assert Path(command[-2]).read_text(encoding="utf-8").startswith('{"version": 2')
        Path(command[-1]).write_bytes(command[0].encode())

    monkeypatch.setattr(export, "_run", run)
    recording = tmp_path / "effect.tterec"
    _write_recording(recording)
    export.export_recording(recording, tmp_path / "out.webp", _WEBP, fps=30)
    assert [command[0] for command in commands] == ["agg", "gif2webp"]
    assert "--fps-cap" in commands[0]
    assert commands[0][commands[0].index("--fps-cap") + 1] == "30"
    assert (tmp_path / "out.webp").read_bytes() == b"gif2webp"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["effect.tterec", "out.webp"]


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
