"""Drawer handles: a one-cell strip beside a panel that hides or shows it when clicked."""

from __future__ import annotations

import typing

from rich.segment import Segment
from rich.style import Style
from textual.message import Message
from textual.reactive import reactive
from textual.strip import Strip
from textual.widget import Widget

Side = typing.Literal["left", "bottom"]
"""Where the panel sits relative to its handle: a left panel has a vertical handle, a bottom panel a horizontal one."""

_ARROWS: dict[tuple[Side, bool], str] = {
    ("left", True): "◀",
    ("left", False): "▶",
    ("bottom", True): "▼",
    ("bottom", False): "▲",
}
"""Arrow drawn on a handle for its panel's side and whether the panel is open, pointing the way it will move."""


class DrawerHandle(Widget):
    """A one-column or one-row strip that hides or shows a panel when clicked, labeled with the panel's name."""

    DEFAULT_CSS = """
    DrawerHandle {
        background: $boost;
        color: $text-muted;
    }
    DrawerHandle.-left {
        width: 1;
        height: 1fr;
    }
    DrawerHandle.-bottom {
        width: 1fr;
        height: 1;
    }
    DrawerHandle:hover {
        background: $primary;
        color: $text;
    }
    """

    open: reactive[bool] = reactive(default=True)
    """Whether the panel is shown."""

    class Toggled(Message):
        """Posted when the handle's panel is opened or closed."""

        def __init__(self, handle: DrawerHandle) -> None:
            """Initialize the message for `handle`."""
            super().__init__()
            self.handle = handle

        @property
        def control(self) -> DrawerHandle:
            """Return the handle, so the message can be matched by its id."""
            return self.handle

    def __init__(self, side: Side, label: str, key: str, **kwargs: typing.Any) -> None:
        """Initialize a handle for the panel on `side` named `label`, which `key` also toggles."""
        super().__init__(**kwargs)
        self.side: Side = side
        self.label = label
        self.add_class(f"-{side}")
        self._key = key
        self._update_tooltip()

    def _update_tooltip(self) -> None:
        action = "Hide" if self.open else "Show"
        self.tooltip = f"{action} the {self.label.lower()} ({self._key})"

    def watch_open(self) -> None:
        """Redraw the arrow and announce the change."""
        self._update_tooltip()
        self.refresh()
        self.post_message(DrawerHandle.Toggled(self))

    def on_click(self) -> None:
        """Hide or show the panel."""
        self.toggle()

    def toggle(self) -> None:
        """Hide or show the panel."""
        self.open = not self.open

    def render_line(self, y: int) -> Strip:
        """Draw a guide line with the arrow, and for a horizontal handle the panel's name, in the middle."""
        style = self.rich_style
        arrow = _ARROWS[(self.side, self.open)]
        width = self.size.width
        if self.side == "left":
            middle = self.size.height // 2
            text = arrow if y == middle else "┊"
            return Strip([Segment(text, style if y == middle else style + Style(dim=True))]).adjust_cell_length(
                width, style
            )
        label = f" {arrow} {self.label} {arrow} "
        if width < len(label):
            label = arrow
        left = (width - len(label)) // 2
        line = style + Style(dim=True)
        segments = [
            Segment("┄" * left, line),
            Segment(label, style),
            Segment("┄" * (width - left - len(label)), line),
        ]
        return Strip(segments).adjust_cell_length(width, style)
