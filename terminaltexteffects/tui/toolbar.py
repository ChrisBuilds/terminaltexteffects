"""The text toolbar above the editor: text colors and symbol palettes."""

from __future__ import annotations

import typing

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual.containers import Horizontal
from textual.message import Message
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Button, Static

if typing.TYPE_CHECKING:
    from textual import events
    from textual.app import ComposeResult

    from terminaltexteffects.utils.graphics import Color

Layer = typing.Literal["fg", "bg"]

SYMBOL_GROUPS: dict[str, str] = {
    "Blocks": "█▓▒░▀▄▌▐▖▗▘▝▚▞",
    "Lines": "─│┌┐└┘├┤┬┴┼╭╮╰╯",
    "Double": "═║╔╗╚╝╠╣╦╩╬",
    "Shapes": "●○◆◇■□▲▼◀▶★☆",
    "Arrows": "←↑→↓↖↗↘↙⇐⇑⇒⇓",
}
"""Symbols the toolbar inserts, by group."""

_SYMBOL_WIDTH = 2
_EMPTY_SWATCH = "░░"


class PenSwatch(Static):
    """Shows the text color for one layer, two cells wide, and asks for a new one when clicked."""

    def __init__(self, layer: Layer, **kwargs: typing.Any) -> None:
        """Initialize the swatch for the foreground or background `layer`."""
        super().__init__(**kwargs)
        self.pen_layer: Layer = layer
        self.show(None)

    def show(self, color: Color | None) -> None:
        """Show `color`, or a hatched square when the layer has no color."""
        name = "Fg" if self.pen_layer == "fg" else "Bg"
        text = Text(f"{name} ")
        if color is None:
            text.append(_EMPTY_SWATCH, "dim")
        else:
            text.append("  ", Style(bgcolor=f"#{color.rgb_color}"))
        self.update(text)
        what = "Text color" if self.pen_layer == "fg" else "Background color"
        current = f"#{color.rgb_color}" if color else "none"
        self.tooltip = f"{what} for the selection and for new text ({current}). Click to pick."

    def on_click(self) -> None:
        """Ask for a new color for this layer."""
        self.post_message(TextToolbar.PickColor(self.pen_layer))


class SymbolStrip(Widget):
    """A row of clickable symbols from one group."""

    DEFAULT_CSS = """
    SymbolStrip {
        height: 1;
        width: 1fr;
    }
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        """Initialize the strip with the first group's symbols."""
        super().__init__(**kwargs)
        self.symbols = next(iter(SYMBOL_GROUPS.values()))
        self._hover: int | None = None
        self.tooltip = "Click a symbol to insert it at the cursor"

    def show_group(self, group: str) -> None:
        """Show the symbols of `group`."""
        self.symbols = SYMBOL_GROUPS[group]
        self.refresh()

    def render_line(self, y: int) -> Strip:
        """Render the symbols, each centered in two cells, with the one under the mouse highlighted."""
        if y:
            return Strip.blank(self.size.width, self.rich_style)
        base = self.rich_style
        hover = base + Style(reverse=True)
        segments = [
            Segment(f"{symbol} ", hover if index == self._hover else base) for index, symbol in enumerate(self.symbols)
        ]
        return Strip(segments).adjust_cell_length(self.size.width, base)

    def _index_at(self, x: int) -> int | None:
        index = x // _SYMBOL_WIDTH
        return index if 0 <= index < len(self.symbols) else None

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Highlight the symbol under the mouse."""
        index = self._index_at(event.x)
        if index != self._hover:
            self._hover = index
            self.refresh()

    def on_leave(self) -> None:
        """Clear the highlight when the mouse leaves."""
        self._hover = None
        self.refresh()

    def on_click(self, event: events.Click) -> None:
        """Insert the clicked symbol."""
        index = self._index_at(event.x)
        if index is not None:
            self.post_message(TextToolbar.InsertSymbol(self.symbols[index]))


class TextToolbar(Horizontal):
    """Text color swatches, a button to clear colors, and symbol palettes for the editor.

    None of its parts take focus, so the editor keeps the cursor and selection while the toolbar is used.
    """

    DEFAULT_CSS = """
    TextToolbar {
        height: 1;
    }
    TextToolbar PenSwatch {
        width: auto;
        margin-right: 1;
    }
    TextToolbar Button {
        min-width: 0;
        margin-right: 1;
    }
    TextToolbar .divider {
        width: 1;
        margin-right: 1;
        color: $primary;
    }
    """

    class PickColor(Message):
        """Posted to pick the text color for `layer`."""

        def __init__(self, layer: Layer) -> None:
            """Initialize the message for the foreground or background `layer`."""
            super().__init__()
            self.layer: Layer = layer

    class ClearColor(Message):
        """Posted to clear the text colors and the colors of the selection."""

    class InsertSymbol(Message):
        """Posted to insert `symbol` at the cursor."""

        def __init__(self, symbol: str) -> None:
            """Initialize the message with the `symbol` to insert."""
            super().__init__()
            self.symbol = symbol

    def __init__(self, **kwargs: typing.Any) -> None:
        """Initialize the toolbar with the first symbol group selected."""
        super().__init__(**kwargs)
        self.group = next(iter(SYMBOL_GROUPS))

    def compose(self) -> ComposeResult:
        """Create the color swatches, the clear button, the group buttons, and the symbols."""
        yield PenSwatch("fg", id="pen-fg")
        yield PenSwatch("bg", id="pen-bg")
        yield self._button("Clear", "clear-color", "Clear the text colors and the selection's colors")
        yield Static("│", classes="divider")
        for group, symbols in SYMBOL_GROUPS.items():
            button = self._button(symbols[0], f"group-{group.lower()}", f"{group}: show these symbols")
            button.variant = "primary" if group == self.group else "default"
            yield button
        yield Static("│", classes="divider")
        yield SymbolStrip(id="symbols")

    @staticmethod
    def _button(label: str, button_id: str, tooltip: str) -> Button:
        button = Button(label, id=button_id, compact=True)
        button.can_focus = False
        button.tooltip = tooltip
        return button

    def show_colors(self, fg: Color | None, bg: Color | None) -> None:
        """Show the current text colors."""
        self.query_one("#pen-fg", PenSwatch).show(fg)
        self.query_one("#pen-bg", PenSwatch).show(bg)

    def select_group(self, group: str) -> None:
        """Show the symbols of `group` and mark its button."""
        self.group = group
        for name in SYMBOL_GROUPS:
            self.query_one(f"#group-{name.lower()}", Button).variant = "primary" if name == group else "default"
        self.query_one(SymbolStrip).show_group(group)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Clear the colors or switch the symbol group."""
        event.stop()
        button_id = event.button.id or ""
        if button_id == "clear-color":
            self.post_message(TextToolbar.ClearColor())
        elif button_id.startswith("group-"):
            self.select_group(button_id.removeprefix("group-").capitalize())
