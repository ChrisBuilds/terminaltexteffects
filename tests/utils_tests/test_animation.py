"""Cover drawing recordings as GIF and WebP animations with Pillow: parsing, drawing, timing, and encoding."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.engine._recording import RecordingHeader, RecordingWriter

# Pillow is only installed on Python 3.10 and later.
pytest.importorskip("PIL")

from PIL import Image, ImageChops, ImageStat

from terminaltexteffects.utils import _animation as animation
from terminaltexteffects.utils._animation import BACKGROUND, FOREGROUND, Cell

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
    rows = animation.parse_frame("\x1b[38;2;255;0;0ma\x1b[48;5;21mb\n\x1b[0mc\x1b[1;7md", 2, 2)
    assert rows[0] == (Cell("a", RED, BACKGROUND), Cell("b", RED, (0, 0, 255)))
    assert rows[1] == (
        Cell("c", FOREGROUND, BACKGROUND),
        Cell("d", FOREGROUND, BACKGROUND, animation.BOLD | animation.REVERSE),
    )


def test_parse_frame_gives_wide_symbols_two_cells() -> None:
    """A wide symbol is followed by an empty cell it covers, and short frames are padded with blank cells."""
    rows = animation.parse_frame("字", 3, 2)
    blank = Cell(" ", FOREGROUND, BACKGROUND)
    assert rows == [(Cell("字", FOREGROUND, BACKGROUND), Cell("", FOREGROUND, BACKGROUND), blank), (blank,) * 3]


def test_frame_times_skip_frames_evenly_and_hold_the_first() -> None:
    """Halving the frame rate keeps every other frame, and later frames start after the start hold."""
    assert list(animation.frame_times(5, 60, 30, 0.5)) == [(0, 0), (2, 533), (4, 567)]
    assert [index for index, _ in animation.frame_times(4, 30, 60, 0)] == [0, 1, 2, 3]


def test_gif_delays_round_to_two_hundredths_and_skip_frames_that_would_play_too_fast() -> None:
    """60 fps frames play at 50 fps, the later of two frames rounded to one start replacing the earlier."""
    assert animation.gif_delays([0, 17, 33, 50, 67], 83) == [(0, 2), (1, 2), (3, 2), (4, 2)]
    assert animation.gif_delays([0, 125, 250], 2375) == [(0, 12), (1, 12), (2, 214)]


def test_gif_palette_keeps_exact_colors_when_they_fit() -> None:
    """Images with 255 colors or fewer get exactly those colors, so GIF output keeps them."""
    image = Image.new("RGB", (2, 1), BACKGROUND)
    image.putpixel((1, 0), RED)
    palette = animation.gif_palette([image])
    assert sorted(zip(palette[::3], palette[1::3], palette[2::3])) == sorted([BACKGROUND, RED])


@pytest.fixture(scope="module")
def fonts() -> animation.Fonts:
    """Load the default font, skipping when it is not installed."""
    try:
        return animation.Fonts()
    except animation.RenderError:
        pytest.skip("no monospace font is installed")


def test_drawer_redraws_only_changed_frames(fonts: animation.Fonts) -> None:
    """Drawing the same cells again reports no change, and block elements fill their part of the cell."""
    drawer = animation.FrameDrawer(fonts, 2, 1)
    assert drawer.draw(animation.parse_frame("\x1b[38;2;255;0;0m█▀", 2, 1))
    assert not drawer.draw(animation.parse_frame("\x1b[38;2;255;0;0m█▀", 2, 1))
    pad, width, height = drawer.padding, fonts.cell_width, fonts.cell_height
    assert drawer.image.getpixel((pad + width // 2, pad + height - 1)) == RED
    assert drawer.image.getpixel((pad + width + width // 2, pad + height - 1)) == BACKGROUND
    assert drawer.image.getpixel((pad + width + width // 2, pad)) == RED


def test_cleared_cells_leave_no_ink_behind(fonts: animation.Fonts) -> None:
    """Glyphs stay inside their cells, so redrawing only changed cells matches drawing the frame from scratch."""
    drawer = animation.FrameDrawer(fonts, 4, 1)
    for frame in ("#W%&", " W ", "    "):
        drawer.draw(animation.parse_frame(frame, 4, 1))
        fresh = animation.FrameDrawer(fonts, 4, 1)
        fresh.draw(animation.parse_frame(frame, 4, 1))
        assert ImageChops.difference(drawer.image, fresh.image).getbbox() is None


def test_draw_frames_merges_unchanged_frames(tmp_path: Path, fonts: animation.Fonts) -> None:
    """A repeated frame lengthens the frame before it, and the end is when the recording ends."""
    write_recording(tmp_path / "demo.tterec", ["ab\ncd", "ab\ncd", "ef\ngh"])
    frames = animation.draw_frames(tmp_path / "demo.tterec", tmp_path, fps=10, fonts=fonts)
    assert [path.name for path in frames.paths] == ["000000.png", "000001.png"]
    assert (frames.starts, frames.end) == ([0, 200], 300)


def test_webp_keeps_every_frame_and_its_duration(tmp_path: Path, fonts: animation.Fonts) -> None:
    """WebP output is lossless, and the last frame is held for the end hold."""
    write_recording(tmp_path / "demo.tterec", ["ab\ncd", "ab\ncd", "ef\ngh"])
    frames = animation.draw_frames(tmp_path / "demo.tterec", tmp_path, fps=10, fonts=fonts)
    animation.write_webp(frames, tmp_path / "demo.webp", end_hold=1.0)
    with Image.open(tmp_path / "demo.webp") as webp:
        assert getattr(webp, "n_frames", 1) == 2
        for index, path in enumerate(frames.paths):
            webp.seek(index)
            webp.load()
            assert webp.info["duration"] == [200, 1100][index]
            with Image.open(path) as expected:
                assert ImageChops.difference(webp.convert("RGB"), expected.convert("RGB")).getbbox() is None


def test_gif_draws_each_frame_over_the_last(tmp_path: Path, fonts: animation.Fonts) -> None:
    """Each GIF frame shows the drawn frame, within the precision of Pillow's palette lookup."""
    write_recording(tmp_path / "demo.tterec", ["ab\ncd", "\x1b[38;2;255;0;0mab\x1b[0m\ncd", "ab\ncx"])
    frames = animation.draw_frames(tmp_path / "demo.tterec", tmp_path, fps=10, fonts=fonts)
    animation.write_gif(frames, tmp_path / "demo.gif", end_hold=1.0)
    with Image.open(tmp_path / "demo.gif") as gif:
        assert getattr(gif, "n_frames", 1) == 3
        for index, path in enumerate(frames.paths):
            gif.seek(index)
            assert gif.info["duration"] == [100, 100, 1100][index]
            with Image.open(path) as expected:
                difference = ImageChops.difference(gif.convert("RGB"), expected.convert("RGB"))
                assert max(high for _, high in ImageStat.Stat(difference).extrema) <= 8


def test_missing_glyphs_come_from_a_fallback_font(fonts: animation.Fonts) -> None:
    """Symbols the main font draws keep it, and half-width katakana, which DejaVu Sans Mono lacks, fall back."""
    assert fonts.for_symbol("a", fonts.regular) is fonts.regular
    fallback = fonts.for_symbol("ｱ", fonts.regular)
    if fallback is fonts.regular:
        pytest.skip("no installed font has half-width katakana")
    assert animation._has_glyph(fallback, "ｱ")


def test_draw_frames_keeps_the_last_frame_when_skipping_frames(tmp_path: Path, fonts: animation.Fonts) -> None:
    """Halving the frame rate still shows the final recorded frame, at its own time."""
    write_recording(tmp_path / "demo.tterec", ["ab\ncd", "ef\ngh", "ij\nkl", "mn\nop"])
    frames = animation.draw_frames(tmp_path / "demo.tterec", tmp_path, fps=5, fonts=fonts)
    assert (frames.starts, frames.end) == ([0, 200, 300], 400)
