"""Tests for converting recordings to GIF and WebP."""

from __future__ import annotations

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


def test_missing_pillow_names_the_install_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without Pillow, GIF and WebP should say how to install it, and tterec should still work."""
    monkeypatch.setattr(export, "pillow_available", lambda: False)
    monkeypatch.setattr(export, "PILLOW_PYTHON", True)
    assert export.format_problem(export.FORMATS[0]) is None
    assert export.format_problem(_WEBP) == "WebP export needs Pillow; install it with: " + export.INSTALL_HINT
    monkeypatch.setattr(export, "PILLOW_PYTHON", False)
    assert export.format_problem(_GIF) == "GIF export needs Python 3.10 or later."
    with pytest.raises(export.ExportError, match=r"Python 3\.10"):
        export.export_recording(Path("effect.tterec"), Path("out.gif"), _GIF, fps=30)


@pytest.mark.parametrize(("fmt", "magic"), [(_GIF, b"GIF89a"), (_WEBP, b"RIFF")])
def test_export_writes_the_format(tmp_path: Path, fmt: export.ExportFormat, magic: bytes) -> None:
    """GIF and WebP output should be written to the output path, leaving no temporary files beside it."""
    pytest.importorskip("PIL")
    recording = tmp_path / "effect.tterec"
    _write_recording(recording)
    output = tmp_path / f"out{fmt.suffix}"
    assert export.export_recording(recording, output, fmt, fps=30) == frozenset()
    assert output.read_bytes().startswith(magic)
    assert sorted(path.name for path in tmp_path.iterdir()) == ["effect.tterec", output.name]


def test_export_reports_drawing_then_encoding(tmp_path: Path) -> None:
    """Progress should count the recorded frames while drawing, then the frames written while encoding."""
    pytest.importorskip("PIL")
    recording = tmp_path / "effect.tterec"
    _write_recording(recording)
    steps: list[tuple[str, int, int | None]] = []
    export.export_recording(
        recording,
        tmp_path / "out.webp",
        _WEBP,
        fps=30,
        on_progress=lambda step, count, total: steps.append((step, count, total)),
    )
    assert steps == [
        (export.DRAWING, 1, None),
        (export.DRAWING, 2, None),
        (export.ENCODING, 1, 2),
        (export.ENCODING, 2, 2),
    ]


def test_failed_export_keeps_the_existing_file(tmp_path: Path) -> None:
    """A conversion that fails should leave the previous output untouched and no temporary file."""
    pytest.importorskip("PIL")
    recording = tmp_path / "effect.tterec"
    with RecordingWriter(recording, RecordingHeader("test", 2, 1, 10)):
        pass
    output = tmp_path / "out.gif"
    output.write_bytes(b"previous")
    with pytest.raises(export.ExportError, match="has no frames"):
        export.export_recording(recording, output, _GIF, fps=30)
    assert output.read_bytes() == b"previous"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["effect.tterec", "out.gif"]
