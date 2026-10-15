"""Cover the direct WebP demo renderer's frame parsing, drawing, and timing, without running `img2webp`."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine._recording import RecordingHeader, RecordingWriter
from tools import render_webp
from tools.render_webp import BACKGROUND, FOREGROUND, Cell, Encoding

if TYPE_CHECKING:
    from pathlib import Path

RED = (255, 0, 0)


def write_recording(path: Path, frames: list[str], frame_rate: int = 10) -> None:
    """Write a two-cell, two-row recording holding `frames`."""
    with RecordingWriter(path, RecordingHeader("test", 2, 2, frame_rate)) as writer:
        writer.begin_segment("test")
        for frame in frames:
            writer.write_frame(frame)


def test_parse_frame_reads_truecolor_xterm_and_reset_sequences() -> None:
    """Colors apply to the symbols after them and carry over to the next row until reset."""
    rows = render_webp.parse_frame("\x1b[38;2;255;0;0ma\x1b[48;5;21mb\n\x1b[0mc\x1b[1;7md", 2, 2)
    assert rows[0] == (Cell("a", RED, BACKGROUND), Cell("b", RED, (0, 0, 255)))
    assert rows[1] == (
        Cell("c", FOREGROUND, BACKGROUND),
        Cell("d", FOREGROUND, BACKGROUND, render_webp.BOLD | render_webp.REVERSE),
    )


def test_parse_frame_gives_wide_symbols_two_cells() -> None:
    """A wide symbol is followed by an empty cell it covers, and short frames are padded with blank cells."""
    rows = render_webp.parse_frame("字", 3, 2)
    blank = Cell(" ", FOREGROUND, BACKGROUND)
    assert rows == [(Cell("字", FOREGROUND, BACKGROUND), Cell("", FOREGROUND, BACKGROUND), blank), (blank,) * 3]


def test_frame_times_skip_frames_evenly_and_hold_the_first() -> None:
    """Halving the frame rate keeps every other frame, and later frames start after the start hold."""
    assert list(render_webp.frame_times(5, 60, 30, 0.5)) == [(0, 0), (2, 533), (4, 567)]
    assert [index for index, _ in render_webp.frame_times(4, 30, 60, 0)] == [0, 1, 2, 3]


def test_near_lossless_is_a_file_option() -> None:
    """Lossless output passes no near-lossless level, and a level is set once for the whole file."""
    assert render_webp.LOSSLESS.file_options() == ["-min_size", "-loop", "0"]
    assert Encoding(60).file_options()[-2:] == ["-near_lossless", "60"]


@pytest.fixture(scope="module")
def fonts() -> render_webp.Fonts:
    """Load the default font, skipping when it is not installed."""
    try:
        return render_webp.Fonts(render_webp.FONT)
    except render_webp.RenderError:
        pytest.skip("DejaVu Sans Mono is not installed")


def test_drawer_redraws_only_changed_frames(fonts: render_webp.Fonts) -> None:
    """Drawing the same cells again reports no change, and block elements fill their part of the cell."""
    drawer = render_webp.FrameDrawer(fonts, 2, 1)
    assert drawer.draw(render_webp.parse_frame("\x1b[38;2;255;0;0m█▀", 2, 1))
    assert not drawer.draw(render_webp.parse_frame("\x1b[38;2;255;0;0m█▀", 2, 1))
    pad, width, height = drawer.padding, fonts.cell_width, fonts.cell_height
    assert drawer.image.getpixel((pad + width // 2, pad + height - 1)) == RED
    assert drawer.image.getpixel((pad + width + width // 2, pad + height - 1)) == BACKGROUND
    assert drawer.image.getpixel((pad + width + width // 2, pad)) == RED


def test_render_merges_unchanged_frames_and_holds_the_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fonts: render_webp.Fonts,
) -> None:
    """Repeated frames lengthen the frame before them, and the last frame is held for the end hold."""
    write_recording(tmp_path / "demo.tterec", ["ab\ncd", "ab\ncd", "ef\ngh"])
    arguments: list[str] = []

    def run(command: list[str], **kwargs: Path) -> subprocess.CompletedProcess[str]:
        work = kwargs["cwd"]
        arguments.extend((work / command[1]).read_text(encoding="utf-8").split())
        (work / "out.webp").write_bytes(b"webp")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(render_webp.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(render_webp.subprocess, "run", run)
    render_webp.render_webp(tmp_path / "demo.tterec", tmp_path / "demo.webp", fps=10, fonts=fonts, end_hold=1.0)
    assert (tmp_path / "demo.webp").read_bytes() == b"webp"
    assert arguments == [
        *render_webp.LOSSLESS.file_options(),
        *("-d", "200", "-lossless", "000000.png"),
        *("-d", "1100", "-lossless", "000001.png"),
        *("-o", "out.webp"),
    ]


def test_missing_glyphs_come_from_a_fallback_font(fonts: render_webp.Fonts) -> None:
    """Symbols the main font draws keep it, and half-width katakana, which DejaVu Sans Mono lacks, fall back."""
    assert fonts.for_symbol("a", fonts.regular) is fonts.regular
    fallback = fonts.for_symbol("ｱ", fonts.regular)
    if fallback is fonts.regular:
        pytest.skip("no installed font has half-width katakana")
    assert render_webp._has_glyph(fallback, "ｱ")
