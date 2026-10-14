"""Tests for converting effect frames to Textual strips."""

from __future__ import annotations

import itertools
import time
from typing import TYPE_CHECKING

from rich.style import Style

from terminaltexteffects.tui.frames import FrameStream, RecordedFrames, frame_to_strips

if TYPE_CHECKING:
    from collections.abc import Iterator

    from terminaltexteffects.tui.frames import Frame


def test_frame_rows_become_styled_strips() -> None:
    """Each frame row should become a strip with the SGR styles applied and adjacent runs merged."""
    frame = "\x1b[38;2;255;0;0ma\x1b[0m\x1b[38;2;255;0;0mb\x1b[0m c\n\x1b[1;48;5;4md\x1b[0m"
    first, second = frame_to_strips(frame)
    assert first.text == "ab c"
    segments = list(first)
    assert segments[0].text == "ab"
    assert segments[0].style == Style.parse("#ff0000")
    assert segments[1].style is None
    assert second.text == "d"
    style = next(iter(second)).style
    assert style is not None
    assert style.bold
    assert style.bgcolor is not None


def test_wide_characters_keep_their_cell_width() -> None:
    """Wide symbols should occupy two cells in the strip."""
    (strip,) = frame_to_strips("\x1b[31m中\x1b[0mx")
    assert strip.cell_length == 3


def test_unchanged_rows_reuse_the_previous_strip() -> None:
    """Rows equal to the previous frame's rows should keep the same strip object."""
    first = frame_to_strips("\x1b[31mab\x1b[0m\ncd")
    second = frame_to_strips("\x1b[31mab\x1b[0m\nce", ["\x1b[31mab\x1b[0m", "cd"], first)

    assert second[0] is first[0]
    assert second[1] is not first[1]
    assert second[1].text == "ce"


def _drain(stream: FrameStream | RecordedFrames) -> list[Frame]:
    result = []
    deadline = time.monotonic() + 10
    while not stream.finished and time.monotonic() < deadline:
        frame = stream.poll()
        if frame is None:
            time.sleep(0.001)
        else:
            result.append(frame)
    return result


def test_frame_stream_produces_every_frame_in_order() -> None:
    """A stream should convert every frame on its thread, then finish."""
    frames = [f"frame {index}\nsame" for index in range(30)]
    stream = FrameStream(iter(frames), ahead=2)
    stream.start()

    produced = _drain(stream)

    assert [frame[0].text for frame in produced] == _first_rows(frames)
    assert all(frame[1] is produced[0][1] for frame in produced)
    assert stream.error is None
    replay = RecordedFrames(produced)
    assert _drain(replay) == produced


def _first_rows(frames: list[str]) -> list[str]:
    return [frame.split("\n")[0] for frame in frames]


def test_frame_stream_reports_effect_errors_and_stops_when_closed() -> None:
    """An exception from the effect should end the stream with the error, and closing should stop the thread."""

    def failing() -> Iterator[str]:
        yield "one"
        msg = "broken"
        raise RuntimeError(msg)

    stream = FrameStream(failing())
    stream.start()
    assert [frame[0].text for frame in _drain(stream)] == ["one"]
    assert isinstance(stream.error, RuntimeError)

    endless = FrameStream(itertools.repeat("x"), ahead=1)
    endless.start()
    endless.close()
    endless._thread.join(timeout=2)
    assert not endless._thread.is_alive()
    assert endless.poll() is None
