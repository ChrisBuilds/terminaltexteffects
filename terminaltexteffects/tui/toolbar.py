"""The text toolbar above the editor: text colors and a symbol palette."""

from __future__ import annotations

import typing

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import events, on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Button, Static

from terminaltexteffects.tui.gradient import GradientChip, TextGradient

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from textual.app import ComposeResult
    from textual.geometry import Offset

    from terminaltexteffects.utils.graphics import Color

Layer = typing.Literal["fg", "bg"]

SYMBOL_GROUPS: dict[str, str] = {
    "Blocks": "█▓▒░▀▄▌▐▖▗▘▝▚▞",
    "Lines": "─│┌┐└┘├┤┬┴┼╭╮╰╯",
    "Double": "═║╔╗╚╝╠╣╦╩╬",
    "Shapes": "●○◆◇■□▲▼◀▶★☆",
    "Arrows": "←↑→↓↖↗↘↙⇐⇑⇒⇓",
}
"""Symbols the palette inserts, by group."""

_CELL = 3
"""Cells per symbol in the palette, so each is an easy target."""
_LABEL_WIDTH = 8
_EMPTY_SWATCH = "░░"


class PenSwatch(Static):
    """A button-like chip that names a color layer, shows its color as a square, and asks for a new one."""

    def __init__(self, layer: Layer, **kwargs: typing.Any) -> None:
        """Initialize the chip for the foreground or background `layer`."""
        super().__init__(**kwargs)
        self.pen_layer: Layer = layer
        self.show(None)

    def show(self, color: Color | None) -> None:
        """Show `color`, or a hatched square when the layer has no color."""
        name = "Text" if self.pen_layer == "fg" else "Background"
        text = Text(f"{name} ")
        if color is None:
            text.append(_EMPTY_SWATCH, "dim")
        else:
            text.append("  ", Style(bgcolor=f"#{color.rgb_color}"))
        self.update(text)
        current = f"#{color.rgb_color}" if color else "none"
        self.tooltip = f"{name} color for the selection and for new text ({current}). Click to pick."

    def on_click(self) -> None:
        """Ask for a new color for this layer."""
        self.post_message(TextToolbar.PickColor(self.pen_layer))


class SymbolGrid(Widget, can_focus=True):
    """Every symbol group as a labeled row of symbols, chosen with the mouse or the arrow keys and Enter."""

    DEFAULT_CSS = f"""
    SymbolGrid {{
        width: {_LABEL_WIDTH + _CELL * max(len(symbols) for symbols in SYMBOL_GROUPS.values())};
        height: {len(SYMBOL_GROUPS) * 2 - 1};
    }}
    """

    BINDINGS: typing.ClassVar = [
        Binding("up", "move(0, -1)", show=False),
        Binding("down", "move(0, 1)", show=False),
        Binding("left", "move(-1, 0)", show=False),
        Binding("right", "move(1, 0)", show=False),
        Binding("enter,space", "choose", "Insert"),
    ]

    class Chosen(Message):
        """Posted when `symbol` is chosen."""

        def __init__(self, symbol: str) -> None:
            """Initialize the message with the chosen `symbol`."""
            super().__init__()
            self.symbol = symbol

    def __init__(self, **kwargs: typing.Any) -> None:
        """Initialize the grid with the first symbol selected."""
        super().__init__(**kwargs)
        self.rows = list(SYMBOL_GROUPS.items())
        self.cursor = (0, 0)
        """Column and row of the selected symbol."""

    @property
    def symbol(self) -> str:
        """Return the selected symbol."""
        column, row = self.cursor
        return self.rows[row][1][column]

    def render_line(self, y: int) -> Strip:
        """Render a group's label and symbols on even lines, and a blank line between groups."""
        base = self.rich_style
        if y % 2 or y // 2 >= len(self.rows):
            return Strip.blank(self.size.width, base)
        row = y // 2
        name, symbols = self.rows[row]
        muted = base + Style(dim=True)
        selected = base + Style(
            color=self.app.theme_variables.get("background", "#000000"),
            bgcolor=self.app.theme_variables.get("secondary", "#00d1ff"),
            bold=True,
        )
        segments = [Segment(name.ljust(_LABEL_WIDTH), muted)]
        for column, symbol in enumerate(symbols):
            style = selected if (column, row) == self.cursor else base
            segments.append(Segment(f" {symbol} ", style))
        return Strip(segments).adjust_cell_length(self.size.width, base)

    def _cell_at(self, offset: Offset) -> tuple[int, int] | None:
        if offset.y % 2 or offset.x < _LABEL_WIDTH:
            return None
        row, column = offset.y // 2, (offset.x - _LABEL_WIDTH) // _CELL
        if row < len(self.rows) and column < len(self.rows[row][1]):
            return column, row
        return None

    def _select(self, cell: tuple[int, int]) -> None:
        if cell != self.cursor:
            self.cursor = cell
            self.refresh()

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Select the symbol under the mouse."""
        cell = self._cell_at(event.offset)
        if cell is not None:
            self._select(cell)

    def on_click(self, event: events.Click) -> None:
        """Choose the clicked symbol."""
        cell = self._cell_at(event.offset)
        if cell is not None:
            self._select(cell)
            self.action_choose()

    def action_move(self, columns: int, rows: int) -> None:
        """Move the selection, wrapping around the edges and keeping it within shorter rows."""
        column, row = self.cursor
        row = (row + rows) % len(self.rows)
        width = len(self.rows[row][1])
        column = (column + columns) % width if columns else min(column, width - 1)
        self._select((column, row))

    def action_choose(self) -> None:
        """Choose the selected symbol."""
        self.post_message(SymbolGrid.Chosen(self.symbol))


class SymbolScreen(ModalScreen[None]):
    """A palette of symbols that opens under the toolbar and inserts each symbol chosen until it is closed."""

    DEFAULT_CSS = """
    SymbolScreen {
        background: $background 0%;
    }
    SymbolScreen > Vertical {
        constrain: inside inside;
        width: auto;
        height: auto;
        padding: 1 2;
        border: round $secondary;
        border-title-color: $text;
        border-subtitle-color: $text-muted;
        background: $surface;
    }
    """

    BINDINGS: typing.ClassVar = [Binding("escape", "close", "Close")]

    def __init__(self, insert: Callable[[str], None], at: Offset) -> None:
        """Initialize the palette to call `insert` with each chosen symbol, with its top-left corner `at`."""
        super().__init__()
        self._insert = insert
        self._at = at

    def compose(self) -> ComposeResult:
        """Create the palette."""
        with Vertical() as panel:
            panel.border_title = "Insert symbol"
            panel.border_subtitle = "Click or Enter inserts · Esc closes"
            panel.styles.offset = (self._at.x, self._at.y)
            yield SymbolGrid()

    def on_mount(self) -> None:
        """Give the grid the keyboard."""
        self.query_one(SymbolGrid).focus()

    @on(SymbolGrid.Chosen)
    def _chosen(self, message: SymbolGrid.Chosen) -> None:
        self._insert(message.symbol)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Close the palette when any mouse button is pressed outside it."""
        if not self.query_one(Vertical).region.contains_point(event.screen_offset):
            event.stop()
            self.dismiss(None)

    def action_close(self) -> None:
        """Close the palette."""
        self.dismiss(None)


class TextToolbar(Horizontal):
    """Text and background color chips, a gradient chip, a button to clear colors, and a symbol palette button.

    None of its parts take focus, so the editor keeps the cursor and selection while the toolbar is used.
    """

    DEFAULT_CSS = """
    TextToolbar {
        height: 1;
    }
    TextToolbar PenSwatch {
        width: auto;
        padding: 0 1;
        margin-right: 1;
        background: $boost;
    }
    TextToolbar PenSwatch:hover {
        background: $primary 40%;
    }
    TextToolbar Button {
        min-width: 0;
        margin-right: 1;
    }
    TextToolbar #symbols {
        margin-left: 2;
    }
    TextToolbar GradientChip {
        margin-right: 1;
        background: $boost;
    }
    TextToolbar GradientChip:hover {
        background: $primary 40%;
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

    class OpenSymbols(Message):
        """Posted to open the symbol palette with its top-left corner at the screen offset `at`."""

        def __init__(self, at: Offset) -> None:
            """Initialize the message with the screen offset `at`."""
            super().__init__()
            self.at = at

    def compose(self) -> ComposeResult:
        """Create the color chips, the gradient chip, the clear button, and the symbols button."""
        yield PenSwatch("fg", id="pen-fg")
        yield PenSwatch("bg", id="pen-bg")
        yield GradientChip(TextGradient(), id="gradient")
        yield self._button("Clear", "clear-color", "Clear the text colors and the selection's colors")
        yield self._button("Ω Symbols ▾", "symbols", "Insert block, line, shape, and arrow symbols")

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Clear the colors or open the symbol palette."""
        event.stop()
        if event.button.id == "clear-color":
            self.post_message(TextToolbar.ClearColor())
        elif event.button.id == "symbols":
            self.post_message(TextToolbar.OpenSymbols(event.button.region.bottom_left))
