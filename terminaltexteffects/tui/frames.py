"""Convert effect frames into Textual strips, and produce them ahead of playback on a background thread."""

from __future__ import annotations

import contextlib
import queue
import re
import threading
import typing
from functools import lru_cache

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

_SGR_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")

Frame = list[Strip]
"""One strip per frame row. Rows that did not change since the previous frame reuse the same `Strip` object."""


@lru_cache(maxsize=4096)
def _sgr_style(parameters: str) -> Style | None:
    """Return the style applied by one SGR parameter string, or `None` for a reset."""
    if parameters in ("", "0"):
        return None
    text = Text.from_ansi(f"\x1b[{parameters}m ")
    if not text.spans:
        return Style.null()
    style = text.spans[0].style
    return style if isinstance(style, Style) else Style.parse(style)


@lru_cache(maxsize=4096)
def _combine(current: Style | None, applied: Style) -> Style:
    """Return `applied` layered over `current`."""
    return applied if current is None else current + applied


@lru_cache(maxsize=512)
def row_to_strip(row: str) -> Strip:
    """Return the strip for one frame row of symbols styled with SGR sequences.

    The engine wraps each symbol in its own style and reset, so symbols are joined into one segment while the style
    they are shown in stays the same. Other escape sequences are not produced by the frame iterator and are ignored.
    """
    parts = _SGR_PATTERN.split(row)
    segments: list[Segment] = []
    style: Style | None = None
    run_style: Style | None = None
    run = parts[0]
    for index in range(1, len(parts), 2):
        applied = _sgr_style(parts[index])
        style = None if applied is None else _combine(style, applied)
        text = parts[index + 1]
        if not text:
            continue
        if style is run_style or style == run_style:
            run += text
        else:
            if run:
                segments.append(Segment(run, run_style))
            run = text
            run_style = style
    if run:
        segments.append(Segment(run, run_style))
    return Strip(segments)


def frame_to_strips(frame: str, previous_rows: Sequence[str] = (), previous: Sequence[Strip] = ()) -> Frame:
    """Return one strip per row of an effect frame.

    Rows equal to the same row of `previous_rows`, the rows of the frame before, reuse its strip from `previous`.
    """
    return _rows_to_strips(frame.split("\n"), previous_rows, previous)


def _rows_to_strips(rows: Sequence[str], previous_rows: Sequence[str], previous: Sequence[Strip]) -> Frame:
    reusable = min(len(previous_rows), len(previous))
    return [
        previous[index] if index < reusable and previous_rows[index] == row else row_to_strip(row)
        for index, row in enumerate(rows)
    ]


class FrameStream:
    """Iterates an effect and converts its frames to strips on a background thread, a few frames ahead.

    Building an effect's animations and producing each frame can take longer than a frame interval, so doing it on
    the UI thread freezes the interface and lowers the frame rate. The thread starts with `start`, and playback takes
    frames with `poll` at its own pace.
    """

    _END = object()

    def __init__(self, frames: Iterable[str], ahead: int = 8) -> None:
        """Initialize a stream over `frames`, usually an effect, keeping up to `ahead` converted frames ready."""
        self._frames = frames
        self._queue: queue.Queue[object] = queue.Queue(maxsize=max(1, ahead))
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._produce, name="tte-frames", daemon=True)
        self.finished = False
        """Whether every frame has been taken, or the effect failed."""
        self.error: Exception | None = None
        """The exception the effect raised, if it failed."""

    def start(self) -> None:
        """Start producing frames."""
        self._thread.start()

    def poll(self) -> Frame | None:
        """Return the next frame, or `None` when none is ready yet or the stream has finished."""
        if self.finished:
            return None
        try:
            item = self._queue.get_nowait()
        except queue.Empty:
            return None
        if item is FrameStream._END:
            self.finished = True
            return None
        if isinstance(item, Exception):
            self.finished = True
            self.error = item
            return None
        return typing.cast("Frame", item)

    def close(self) -> None:
        """Stop producing frames. The thread ends after the frame it is working on."""
        self._stop.set()
        self.finished = True
        with contextlib.suppress(queue.Empty):
            while True:
                self._queue.get_nowait()

    def _produce(self) -> None:
        rows: list[str] = []
        strips: Frame = []
        try:
            for frame in self._frames:
                if self._stop.is_set():
                    return
                new_rows = frame.split("\n")
                strips = _rows_to_strips(new_rows, rows, strips)
                rows = new_rows
                if not self._put(strips):
                    return
        except Exception as error:  # noqa: BLE001
            self._put(error)
            return
        self._put(FrameStream._END)

    def _put(self, item: object) -> bool:
        """Queue `item`, waiting while the queue is full. Return `False` if the stream was closed."""
        while not self._stop.is_set():
            try:
                self._queue.put(item, timeout=0.1)
            except queue.Full:
                continue
            return True
        return False


class RecordedFrames:
    """Replays frames kept from an earlier `FrameStream`, with the same interface."""

    def __init__(self, frames: Sequence[Frame]) -> None:
        """Initialize a replay of `frames`."""
        self._frames = frames
        self._index = 0
        self.finished = False
        self.error: Exception | None = None

    def start(self) -> None:
        """Start the replay. Frames are ready at once."""

    def poll(self) -> Frame | None:
        """Return the next frame, or `None` when the replay has finished."""
        if self._index >= len(self._frames):
            self.finished = True
            return None
        frame = self._frames[self._index]
        self._index += 1
        return frame

    def close(self) -> None:
        """End the replay."""
        self.finished = True
