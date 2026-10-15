"""Cover the demo renderer's recording conversion and demo selection, without running external tools."""

from __future__ import annotations

import argparse
import json
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


def read_cast(path: Path) -> tuple[dict[str, int], list[list[object]]]:
    """Return the asciicast header and events."""
    header, *events = (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines())
    return header, events


def test_cast_holds_only_the_canvas_at_the_frame_period(tmp_path: Path) -> None:
    """Frames are redrawn from the top-left corner every frame period, after the start hold."""
    write_recording(tmp_path / "demo.tterec", ["ab\ncd", "ef\ngh", "ij\nkl"])

    non_ascii = render_demos.recording_to_cast(tmp_path / "demo.tterec", tmp_path / "demo.cast", start_hold=0.5)

    header, events = read_cast(tmp_path / "demo.cast")
    assert header == {"version": 2, "width": 2, "height": 2}
    assert events == [
        [0.0, "o", "\x1b[?25l\x1b[2J\x1b[Hab\r\ncd"],
        [0.6, "o", "\x1b[Hef\r\ngh"],
        [0.7, "o", "\x1b[Hij\r\nkl"],
    ]
    assert not non_ascii


def test_cast_reports_non_ascii_frames(tmp_path: Path) -> None:
    """Non-ASCII symbols select the `resvg` renderer."""
    write_recording(tmp_path / "demo.tterec", ["ab\ncd", "aé\ncd"])

    assert render_demos.recording_to_cast(tmp_path / "demo.tterec", tmp_path / "demo.cast", start_hold=0)


def test_every_builtin_effect_has_a_demo() -> None:
    """Demos default to each built-in effect with its default options."""
    demos = render_demos.demos()
    assert list(demos) == render_demos.builtin_effects()
    assert demos["beams"] == render_demos.Demo(effect="beams")


@pytest.mark.parametrize(
    ("value", "expected"),
    [("webp", ["webp"]), ("gif, webp,mp4", ["gif", "webp", "mp4"])],
)
def test_formats_parse(value: str, expected: list[str]) -> None:
    """Formats are a comma-separated subset of the supported formats."""
    assert render_demos.parse_formats(value) == expected


@pytest.mark.parametrize("value", ["", "png", "webp,apng"])
def test_formats_reject_unknown(value: str) -> None:
    """Empty and unsupported formats are rejected."""
    with pytest.raises(argparse.ArgumentTypeError):
        render_demos.parse_formats(value)


def test_near_lossless_demos_exist() -> None:
    """Every near-lossless demo name matches an effect demo or an Effect Guide demo."""
    assert set(render_demos.demos()) | set(render_demos.GUIDE_DEMOS) >= render_demos.NEAR_LOSSLESS_DEMOS
