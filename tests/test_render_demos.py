"""Cover the demo renderer's output and demo selection."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine._recording import RecordingHeader, RecordingWriter
from tools import render_demos

if TYPE_CHECKING:
    from pathlib import Path


def write_recording(path: Path, frames: list[str], frame_rate: int = 10) -> None:
    """Write a two-cell, two-row recording holding `frames`."""
    with RecordingWriter(path, RecordingHeader("test", 2, 2, frame_rate)) as writer:
        writer.begin_segment("test")
        for frame in frames:
            writer.write_frame(frame)


def test_render_writes_each_format_and_reports_sizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each requested format is drawn from one recording and named after the demo."""
    pytest.importorskip("PIL")

    def record(_demo: render_demos.Demo, path: Path) -> None:
        write_recording(path, ["ab\ncd", "ef\ngh"])

    monkeypatch.setattr(render_demos, "record", record)
    message = render_demos.render(
        "beams",
        render_demos.Demo(effect="beams"),
        tmp_path,
        render_demos.RenderOptions(formats=("gif", "webp")),
    )
    assert (tmp_path / "beams_demo.gif").read_bytes().startswith(b"GIF89a")
    assert (tmp_path / "beams_demo.webp").read_bytes()[8:12] == b"WEBP"
    assert message.startswith("beams: gif ")
    assert ", webp " in message


def test_every_builtin_effect_has_a_demo() -> None:
    """Demos default to each built-in effect with its default options."""
    demos = render_demos.demos()
    assert list(demos) == render_demos.builtin_effects()
    assert demos["beams"] == render_demos.Demo(effect="beams")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("webp", ["webp"]), ("gif, webp", ["gif", "webp"])],
)
def test_formats_parse(value: str, expected: list[str]) -> None:
    """Formats are a comma-separated subset of the supported formats."""
    assert render_demos.parse_formats(value) == expected


@pytest.mark.parametrize("value", ["", "png", "webp,mp4"])
def test_formats_reject_unknown(value: str) -> None:
    """Empty and unsupported formats are rejected."""
    with pytest.raises(argparse.ArgumentTypeError):
        render_demos.parse_formats(value)
