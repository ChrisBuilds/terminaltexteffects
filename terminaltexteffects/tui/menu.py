"""A context menu that opens where the mouse was right-clicked."""

from __future__ import annotations

import typing

from textual import events, on
from textual.binding import Binding
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import OptionList
from textual.widgets.option_list import Option

if typing.TYPE_CHECKING:
    from collections.abc import Sequence

    from textual.app import ComposeResult
    from textual.geometry import Offset


class MenuItem(typing.NamedTuple):
    """One menu entry: its label, the action id the menu returns, a key hint, and whether it can be chosen now."""

    label: str
    action: str
    key: str = ""
    enabled: bool = True


class ContextRequested(Message):
    """Posted by a widget that was right-clicked, with the screen offset `at` of the click."""

    def __init__(self, at: Offset) -> None:
        """Initialize the message with the click's screen offset `at`."""
        super().__init__()
        self.at = at


RIGHT_BUTTON = 3


class ContextMenu(ModalScreen["str | None"]):
    """Lists actions at a screen position and returns the chosen action id, or `None` when dismissed."""

    DEFAULT_CSS = """
    ContextMenu {
        background: $background 0%;
    }
    ContextMenu > OptionList {
        constrain: inside inside;
        width: auto;
        height: auto;
        max-height: 100%;
        border: round $secondary;
        background: $surface;
        padding: 0;
    }
    ContextMenu > OptionList > .option-list--option {
        padding: 0 1;
    }
    """

    BINDINGS: typing.ClassVar = [Binding("escape", "close", "Close")]

    def __init__(self, items: Sequence[MenuItem | None], at: Offset) -> None:
        """Initialize the menu with `items`, separated by `None`, and its top-left corner `at`."""
        super().__init__()
        self._items = list(items)
        self._at = at

    def compose(self) -> ComposeResult:
        """Create the menu."""
        entries = [item for item in self._items if item is not None]
        width = max(len(item.label) for item in entries) + 2
        options: list[Option | None] = []
        for item in self._items:
            if item is None:
                options.append(None)
                continue
            options.append(Option(f"{item.label.ljust(width)}{item.key}", id=item.action, disabled=not item.enabled))
        menu = OptionList(*options)
        menu.styles.offset = (self._at.x, self._at.y)
        yield menu

    def on_mount(self) -> None:
        """Give the menu the keyboard, with the first available entry highlighted."""
        menu = self.query_one(OptionList)
        menu.focus()
        menu.highlighted = next((index for index, option in enumerate(menu.options) if not option.disabled), None)

    @on(OptionList.OptionSelected)
    def _selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        self.dismiss(event.option.id)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Close the menu when the mouse is pressed outside it."""
        if event.widget is self:
            self.dismiss(None)

    def action_close(self) -> None:
        """Close the menu."""
        self.dismiss(None)
