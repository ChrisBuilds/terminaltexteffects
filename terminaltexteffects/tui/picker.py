"""Color picker dialog for color options in the TUI.

The dialog edits one color, or the list of stops of a gradient option. Colors are chosen from the XTerm-256
palette, typed as hex, or mixed with hue, saturation, and lightness bars. Palette picks keep their XTerm index, so
they stay XTerm colors on the command line; any other change produces an RGB hex color.
"""

from __future__ import annotations

import colorsys
import typing

from rich.segment import Segment
from rich.style import Style
from textual import events, on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Static

from terminaltexteffects.utils.graphics import Color, Gradient

if typing.TYPE_CHECKING:
    from textual.app import ComposeResult
    from textual.geometry import Size

_CELL_WIDTH = 2


def _palette_layout() -> dict[tuple[int, int], int]:
    """Return the XTerm palette laid out as `(row, column)` cells mapped to color indices.

    The 16 system colors fill the first row. The 6x6x6 color cube follows as six 6x6 blocks, three across and two
    down, with red fixed per block, green down each block, and blue across it. The 24 grays fill the last two rows.
    """
    layout: dict[tuple[int, int], int] = {}
    for index in range(16):
        layout[(0, index)] = index
    for red in range(6):
        block_row, block_column = divmod(red, 3)
        for green in range(6):
            for blue in range(6):
                layout[(2 + block_row * 6 + green, block_column * 6 + blue)] = 16 + red * 36 + green * 6 + blue
    for offset in range(24):
        row, column = divmod(offset, 12)
        layout[(15 + row, column)] = 232 + offset
    return layout


_PALETTE = _palette_layout()
_PALETTE_ROWS = max(row for row, _ in _PALETTE) + 1
_PALETTE_COLUMNS = max(column for _, column in _PALETTE) + 1


def contrast_color(color: Color) -> str:
    """Return black or white hex, whichever reads better on `color`."""
    red, green, blue = color.rgb_ints
    return "000000" if 0.299 * red + 0.587 * green + 0.114 * blue > 140 else "ffffff"


def color_to_hls(color: Color) -> tuple[float, float, float]:
    """Return the hue, lightness, and saturation of `color`, each from 0 to 1."""
    red, green, blue = (channel / 255 for channel in color.rgb_ints)
    return colorsys.rgb_to_hls(red, green, blue)


def hls_to_color(hue: float, lightness: float, saturation: float) -> Color:
    """Return the RGB `Color` for hue, lightness, and saturation values from 0 to 1."""
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return Color(f"{round(red * 255):02x}{round(green * 255):02x}{round(blue * 255):02x}")


class PaletteGrid(Widget, can_focus=True):
    """A grid of the XTerm-256 colors. Arrow keys move the cursor, and Enter or a click picks a color."""

    DEFAULT_CSS = f"""
    PaletteGrid {{
        width: {_PALETTE_COLUMNS * _CELL_WIDTH};
        height: {_PALETTE_ROWS};
    }}
    """

    BINDINGS: typing.ClassVar = [
        Binding("up", "move(-1, 0)", "Up", show=False),
        Binding("down", "move(1, 0)", "Down", show=False),
        Binding("left", "move(0, -1)", "Left", show=False),
        Binding("right", "move(0, 1)", "Right", show=False),
        Binding("enter,space", "pick", "Pick", show=False),
    ]

    class Picked(Message):
        """Posted when a palette color is picked."""

        def __init__(self, color: Color) -> None:
            """Initialize the message with the picked `color`."""
            super().__init__()
            self.color = color

    def __init__(self, *, id: str | None = None) -> None:  # noqa: A002
        """Initialize the grid with the cursor on the first color."""
        super().__init__(id=id)
        self.cursor = (0, 0)
        self.selected: int | None = None

    def select(self, color: Color) -> None:
        """Mark `color` as selected if it is a palette color, and move the cursor to it."""
        self.selected = color.xterm_color
        for position, index in _PALETTE.items():
            if index == self.selected:
                self.cursor = position
        self.refresh()

    def render_line(self, y: int) -> Strip:
        """Render one row of palette cells."""
        segments = []
        for column in range(_PALETTE_COLUMNS):
            index = _PALETTE.get((y, column))
            if index is None:
                segments.append(Segment(" " * _CELL_WIDTH, self.rich_style))
                continue
            color = Color(index)
            marker = "  "
            if (y, column) == self.cursor and self.has_focus:
                marker = "[]"
            elif index == self.selected:
                marker = "<>"
            segments.append(Segment(marker, Style(color=f"#{contrast_color(color)}", bgcolor=f"#{color.rgb_color}")))
        return Strip(segments).crop_extend(0, self.size.width, self.rich_style)

    def action_move(self, rows: int, columns: int) -> None:
        """Move the cursor to the nearest palette cell in the given direction."""
        row, column = self.cursor
        if columns:
            target = (row, column + columns)
            if target in _PALETTE:
                self.cursor = target
        else:
            next_row = row + rows
            while 0 <= next_row < _PALETTE_ROWS:
                cells = [cell_column for cell_row, cell_column in _PALETTE if cell_row == next_row]
                if cells:
                    self.cursor = (next_row, min(cells, key=lambda cell_column: abs(cell_column - column)))
                    break
                next_row += rows
        self.refresh()

    def action_pick(self) -> None:
        """Pick the color under the cursor."""
        index = _PALETTE[self.cursor]
        self.selected = index
        self.refresh()
        self.post_message(PaletteGrid.Picked(Color(index)))

    def on_click(self, event: events.Click) -> None:
        """Pick the clicked color."""
        position = (event.y, event.x // _CELL_WIDTH)
        if position in _PALETTE:
            self.cursor = position
            self.action_pick()

    def on_focus(self) -> None:
        """Show the cursor."""
        self.refresh()

    def on_blur(self) -> None:
        """Hide the cursor."""
        self.refresh()


ChannelName = typing.Literal["hue", "saturation", "lightness"]


class ChannelBar(Widget, can_focus=True):
    """A one-row bar for one HSL channel, showing the colors it would produce.

    Left and Right adjust the value, Shift moves in bigger steps, and a click or drag sets it.
    """

    DEFAULT_CSS = """
    ChannelBar {
        width: 1fr;
        height: 1;
    }
    """

    BINDINGS: typing.ClassVar = [
        Binding("left", "nudge(-0.01)", "Less", show=False),
        Binding("right", "nudge(0.01)", "More", show=False),
        Binding("shift+left", "nudge(-0.1)", "Much less", show=False),
        Binding("shift+right", "nudge(0.1)", "Much more", show=False),
    ]

    class Changed(Message):
        """Posted when the user changes the bar's value."""

        def __init__(self, bar: ChannelBar) -> None:
            """Initialize the message for `bar`."""
            super().__init__()
            self.bar = bar

    def __init__(self, channel: ChannelName, *, id: str | None = None) -> None:  # noqa: A002
        """Initialize a bar for `channel`."""
        super().__init__(id=id)
        self.channel: ChannelName = channel
        self.value = 0.0
        self.hls = (0.0, 0.5, 1.0)

    def show(self, hls: tuple[float, float, float]) -> None:
        """Show the bar for the color `hls`, with the marker at this bar's channel."""
        self.hls = hls
        self.value = hls[("hue", "lightness", "saturation").index(self.channel)]
        self.refresh()

    def _color_at(self, value: float) -> Color:
        hue, lightness, saturation = self.hls
        if self.channel == "hue":
            # Show every hue at full strength, so the bar stays readable for grays.
            return hls_to_color(value, 0.5, 1.0)
        if self.channel == "saturation":
            return hls_to_color(hue, lightness if 0.1 < lightness < 0.9 else 0.5, value)
        return hls_to_color(hue, value, saturation)

    def render_line(self, y: int) -> Strip:  # noqa: ARG002
        """Render the bar with a marker at the current value."""
        width = self.size.width
        if width <= 0:
            return Strip([])
        marker = round(self.value * (width - 1))
        segments = []
        for x in range(width):
            color = self._color_at(x / max(1, width - 1))
            text = ("┃" if self.has_focus else "│") if x == marker else " "
            segments.append(Segment(text, Style(color=f"#{contrast_color(color)}", bgcolor=f"#{color.rgb_color}")))
        return Strip(segments, width)

    def _set(self, value: float) -> None:
        self.value = min(1.0, max(0.0, value))
        self.refresh()
        self.post_message(ChannelBar.Changed(self))

    def action_nudge(self, amount: float) -> None:
        """Change the value by `amount`."""
        self._set(self.value + amount)

    def _set_from_x(self, x: int) -> None:
        self._set(x / max(1, self.size.width - 1))

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Set the value at the pointer and follow drags."""
        self.capture_mouse()
        self._set_from_x(event.x)

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Follow a drag."""
        if self.app.mouse_captured is self:
            self._set_from_x(event.x)

    def on_mouse_up(self) -> None:
        """End a drag."""
        self.release_mouse()

    def on_focus(self) -> None:
        """Show the focused marker."""
        self.refresh()

    def on_blur(self) -> None:
        """Show the unfocused marker."""
        self.refresh()


class StopList(Widget, can_focus=True):
    """The stops of a gradient, as chips that wrap onto as many rows as they need. Left and Right select a stop."""

    DEFAULT_CSS = """
    StopList {
        width: 1fr;
        height: auto;
    }
    """

    BINDINGS: typing.ClassVar = [
        Binding("left", "select(-1)", "Previous", show=False),
        Binding("right", "select(1)", "Next", show=False),
    ]

    class Selected(Message):
        """Posted when the user selects a stop."""

    def __init__(self, *, id: str | None = None) -> None:  # noqa: A002
        """Initialize an empty list."""
        super().__init__(id=id)
        self.stops: list[Color] = []
        self.index = 0

    def show(self, stops: list[Color], index: int) -> None:
        """Show `stops` with the stop at `index` selected."""
        self.stops = stops
        self.index = index
        self.refresh(layout=True)

    @staticmethod
    def _label(color: Color) -> str:
        return str(color.xterm_color) if color.xterm_color is not None else color.rgb_color

    def _chips(self, width: int) -> list[tuple[int, int, int]]:
        """Return the row, start column, and end column of each chip, wrapping chips that do not fit `width`."""
        spans = []
        row = x = 0
        for stop in self.stops:
            chip_width = len(self._label(stop)) + 4
            if x and x + chip_width > width:
                row += 1
                x = 0
            spans.append((row, x, x + chip_width))
            x += chip_width + 1
        return spans

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:  # noqa: ARG002
        """Return the number of rows the chips need at `width`."""
        chips = self._chips(width)
        return chips[-1][0] + 1 if chips else 1

    def render_line(self, y: int) -> Strip:
        """Render the chips on row `y`, with the selected stop highlighted."""
        base = self.rich_style
        selected_style = base + Style(bgcolor=self.app.current_theme.primary, bold=True)
        segments = []
        x = 0
        for position, (row, start, _end) in enumerate(self._chips(self.size.width)):
            if row != y:
                continue
            stop = self.stops[position]
            style = selected_style if position == self.index else base
            segments.append(Segment(" " * (start - x), base))
            segments.append(Segment(" ", style))
            segments.append(Segment("██", style + Style(color=f"#{stop.rgb_color}")))
            segments.append(Segment(f" {self._label(stop)} ", style))
            x = start + len(self._label(stop)) + 4
        return Strip(segments).crop_extend(0, self.size.width, base)

    def action_select(self, step: int) -> None:
        """Select the stop `step` places away."""
        self.index = min(len(self.stops) - 1, max(0, self.index + step))
        self.refresh()
        self.post_message(StopList.Selected())

    def on_click(self, event: events.Click) -> None:
        """Select the clicked stop."""
        for position, (row, start, end) in enumerate(self._chips(self.size.width)):
            if row == event.y and start <= event.x < end:
                self.index = position
                self.refresh()
                self.post_message(StopList.Selected())

    def on_focus(self) -> None:
        """Redraw the focused list."""
        self.refresh()


class GradientBar(Widget):
    """A one-row preview of the gradient made by a list of stops."""

    DEFAULT_CSS = """
    GradientBar {
        width: 1fr;
        height: 1;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:  # noqa: A002
        """Initialize an empty preview."""
        super().__init__(id=id)
        self.stops: list[Color] = []

    def show(self, stops: list[Color]) -> None:
        """Preview `stops`."""
        self.stops = list(stops)
        self.refresh()

    def render_line(self, y: int) -> Strip:  # noqa: ARG002
        """Render the gradient across the widget's width."""
        width = self.size.width
        if width <= 0 or not self.stops:
            return Strip.blank(width)
        steps = max(1, width // max(1, len(self.stops) - 1))
        gradient = Gradient(*self.stops, steps=steps)
        segments = [
            Segment(" ", Style(bgcolor=f"#{gradient.get_color_at_fraction(x / max(1, width - 1)).rgb_color}"))
            for x in range(width)
        ]
        return Strip(segments, width)


class ColorScreen(ModalScreen["tuple[Color, ...] | None"]):
    """Edits one color, or the stops of a gradient, and returns them, or `None` when cancelled.

    With `allow_none`, a No color button returns an empty tuple.
    """

    DEFAULT_CSS = """
    ColorScreen {
        align: center middle;
    }
    ColorScreen > Vertical {
        width: 79;
        max-width: 100%;
        height: auto;
        max-height: 100%;
        overflow-y: auto;
        border: round $primary;
        border-title-color: $text;
        border-subtitle-color: $text-muted;
        background: $surface;
        padding: 1 2;
    }
    ColorScreen .stops-row, ColorScreen .buttons {
        height: auto;
        width: 100%;
    }
    ColorScreen .stops-row {
        margin-bottom: 1;
    }
    ColorScreen .stops-row Button {
        min-width: 4;
        margin-left: 1;
    }
    ColorScreen GradientBar {
        margin-bottom: 1;
    }
    ColorScreen #body {
        width: auto;
        height: auto;
    }
    ColorScreen #mixer {
        width: 34;
        height: 17;
        margin-left: 3;
    }
    ColorScreen #preview {
        height: 4;
        content-align: center middle;
        text-style: bold;
        margin-bottom: 1;
    }
    ColorScreen .channel {
        height: 1;
        margin-bottom: 1;
    }
    ColorScreen .channel > Label {
        width: 4;
        color: $text-muted;
    }
    ColorScreen #hex {
        width: 1fr;
        background: $boost;
        padding: 0 1;
    }
    ColorScreen #hex.-invalid {
        color: $text-error;
        background: $error 15%;
    }
    ColorScreen #no-color {
        margin-left: 4;
    }
    ColorScreen .buttons {
        dock: bottom;
        align-horizontal: right;
    }
    ColorScreen .buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS: typing.ClassVar = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "apply", "Apply"),
    ]

    def __init__(
        self,
        title: str,
        colors: typing.Sequence[Color],
        *,
        multiple: bool,
        allow_none: bool = False,
    ) -> None:
        """Initialize the dialog.

        Args:
            title (str): Option name shown in the border.
            colors (Sequence[Color]): Initial colors. Only the first is used unless `multiple` is set.
            multiple (bool): Whether to edit a list of gradient stops.
            allow_none (bool): Whether to offer a No color button, which returns an empty tuple.

        """
        super().__init__()
        self._title = title
        self.multiple = multiple
        self.allow_none = allow_none
        initial = list(colors) or [Color("ffffff")]
        self.stops: list[Color] = initial if multiple else initial[:1]
        self.index = 0
        self.hls = color_to_hls(self.stops[0])

    def compose(self) -> ComposeResult:
        """Create the stop list, palette, mixer, and buttons."""
        with Vertical() as dialog:
            dialog.border_title = f"Colors · {self._title}"
            dialog.border_subtitle = "Esc cancel · Ctrl+S apply"
            if self.multiple:
                with Horizontal(classes="stops-row"):
                    yield StopList(id="stops")
                    yield Button("+", id="add", compact=True, tooltip="Add a stop after the selected one")
                    yield Button("-", id="remove", compact=True, tooltip="Remove the selected stop")
                    yield Button("◀", id="earlier", compact=True, tooltip="Move the selected stop earlier")
                    yield Button("▶", id="later", compact=True, tooltip="Move the selected stop later")
                yield GradientBar(id="gradient")
            with Horizontal(id="body"):
                yield PaletteGrid(id="palette")
                with Vertical(id="mixer"):
                    yield Static(id="preview")
                    with Horizontal(classes="channel"):
                        yield Label("hex")
                        yield Input(id="hex", compact=True, max_length=7)
                    for channel, label in (("hue", "H"), ("saturation", "S"), ("lightness", "L")):
                        with Horizontal(classes="channel"):
                            yield Label(label)
                            yield ChannelBar(typing.cast("ChannelName", channel), id=channel)
                    if self.allow_none:
                        yield Button("⊘ No color", id="no-color", compact=True, tooltip="Remove this color")
                    with Horizontal(classes="buttons"):
                        yield Button("Cancel", id="cancel")
                        yield Button("Apply", variant="primary", id="apply")

    def on_mount(self) -> None:
        """Show the initial colors and focus the palette."""
        self._show(update_hex=True)
        self.query_one(PaletteGrid).focus()

    @property
    def color(self) -> Color:
        """Return the color being edited."""
        return self.stops[self.index]

    def _set_color(self, color: Color, *, update_hex: bool = True, keep_hls: bool = False) -> None:
        self.stops[self.index] = color
        if not keep_hls:
            self.hls = color_to_hls(color)
        self._show(update_hex=update_hex)

    def _show(self, *, update_hex: bool) -> None:
        color = self.color
        preview = self.query_one("#preview", Static)
        preview.styles.background = f"#{color.rgb_color}"
        preview.styles.color = f"#{contrast_color(color)}"
        xterm = f"  ·  xterm {color.xterm_color}" if color.xterm_color is not None else ""
        preview.update(f"{color.rgb_color}{xterm}")
        if update_hex:
            hex_input = self.query_one("#hex", Input)
            with hex_input.prevent(Input.Changed):
                hex_input.value = color.rgb_color
            hex_input.remove_class("-invalid")
        for bar in self.query(ChannelBar):
            bar.show(self.hls)
        self.query_one(PaletteGrid).select(color)
        if self.multiple:
            self.query_one(StopList).show(self.stops, self.index)
            self.query_one(GradientBar).show(self.stops)
            self.query_one("#remove", Button).disabled = len(self.stops) == 1
            self.query_one("#earlier", Button).disabled = self.index == 0
            self.query_one("#later", Button).disabled = self.index == len(self.stops) - 1

    @on(PaletteGrid.Picked)
    def _palette_picked(self, event: PaletteGrid.Picked) -> None:
        self._set_color(event.color)

    @on(Input.Changed, "#hex")
    def _hex_changed(self, event: Input.Changed) -> None:
        text = event.value.strip().removeprefix("#")
        valid = len(text) == 6 and all(character in "0123456789abcdefABCDEF" for character in text)
        event.input.set_class(not valid, "-invalid")
        if valid:
            self._set_color(Color(text), update_hex=False)

    @on(Input.Submitted, "#hex")
    def _hex_submitted(self) -> None:
        self.action_apply()

    @on(ChannelBar.Changed)
    def _channel_changed(self, event: ChannelBar.Changed) -> None:
        hue, lightness, saturation = self.hls
        if event.bar.channel == "hue":
            hue = event.bar.value
        elif event.bar.channel == "saturation":
            saturation = event.bar.value
        else:
            lightness = event.bar.value
        self.hls = (hue, lightness, saturation)
        self._set_color(hls_to_color(hue, lightness, saturation), keep_hls=True)

    @on(StopList.Selected)
    def _stop_selected(self) -> None:
        self.index = self.query_one(StopList).index
        self.hls = color_to_hls(self.color)
        self._show(update_hex=True)

    @on(Button.Pressed, "#add")
    def _add_stop(self) -> None:
        self.stops.insert(self.index + 1, self.color)
        self.index += 1
        self._show(update_hex=True)

    @on(Button.Pressed, "#remove")
    def _remove_stop(self) -> None:
        if len(self.stops) > 1:
            del self.stops[self.index]
            self.index = min(self.index, len(self.stops) - 1)
            self.hls = color_to_hls(self.color)
            self._show(update_hex=True)

    @on(Button.Pressed, "#earlier")
    def _move_earlier(self) -> None:
        self._move(-1)

    @on(Button.Pressed, "#later")
    def _move_later(self) -> None:
        self._move(1)

    def _move(self, step: int) -> None:
        target = self.index + step
        if 0 <= target < len(self.stops):
            self.stops[self.index], self.stops[target] = self.stops[target], self.stops[self.index]
            self.index = target
            self._show(update_hex=True)

    @on(Button.Pressed, "#apply")
    def action_apply(self) -> None:
        """Close the dialog and return the colors."""
        self.dismiss(tuple(self.stops))

    @on(Button.Pressed, "#no-color")
    def _no_color(self) -> None:
        self.dismiss(())

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        """Close the dialog without changing the option."""
        self.dismiss(None)
