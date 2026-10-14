"""Convert effect frames into Textual strips."""

from __future__ import annotations

import re
from functools import lru_cache

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.strip import Strip

_SGR_PATTERN = re.compile(r"\x1b\[([0-9;]*)m")


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


def frame_to_strips(frame: str) -> list[Strip]:
    """Return one strip per row of an effect frame.

    Frames are rows of symbols separated by newlines, styled with SGR sequences. Other escape sequences are not
    produced by the engine's frame iterator and are ignored.
    """
    strips = []
    for row in frame.split("\n"):
        segments: list[Segment] = []
        style: Style | None = None
        run: list[str] = []
        position = 0
        for match in _SGR_PATTERN.finditer(row):
            if match.start() > position:
                run.append(row[position : match.start()])
            applied = _sgr_style(match.group(1))
            new_style = None if applied is None else _combine(style, applied)
            if new_style != style:
                if run:
                    segments.append(Segment("".join(run), style))
                    run = []
                style = new_style
            position = match.end()
        if position < len(row):
            run.append(row[position:])
        if run:
            segments.append(Segment("".join(run), style))
        strips.append(Strip(Segment.simplify(segments)))
    return strips
