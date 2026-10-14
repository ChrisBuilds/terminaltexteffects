"""Textual application for composing text and previewing effects."""

from __future__ import annotations

import typing
from pathlib import Path

from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.screen import ModalScreen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Input,
    Label,
    OptionList,
    Select,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from terminaltexteffects.engine.terminal import Terminal, TerminalConfig
from terminaltexteffects.tui import canvas, colors, frames, options
from terminaltexteffects.tui.files import FileScreen
from terminaltexteffects.tui.picker import ColorScreen

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from textual import events
    from textual.events import Resize
    from textual.timer import Timer

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect
    from terminaltexteffects.utils.graphics import Color

    EffectResourceMap = dict[str, tuple[type[BaseEffect], type[BaseConfig]]]

_TERMINAL_SCOPE = "terminal"
_MAX_UNLIMITED_FPS = 120
_OPTION_COLUMN_WIDTH = 64


class ColorTextArea(TextArea):
    """A plain-text editor that shows input colors carried across edits, and the canvas outline.

    When the canvas is smaller than the editor, cells outside it are dimmed and an outline is drawn just outside it.
    Dragging an outline edge that moves with the canvas anchor resizes the canvas.
    """

    class CanvasResized(Message):
        """Posted while a canvas edge is dragged, with the new width or height, or `None` for an unchanged one."""

        def __init__(self, width: int | None, height: int | None) -> None:
            """Initialize the message with the new canvas `width` and `height`."""
            super().__init__()
            self.width = width
            self.height = height

    def __init__(self, text: str = "", styles: colors.StyleList | None = None, **kwargs: typing.Any) -> None:
        """Initialize the editor with `text` and optional per-character `styles`."""
        super().__init__(text, soft_wrap=False, show_line_numbers=False, tab_behavior="focus", **kwargs)
        self._color_text = text
        self._color_styles: colors.StyleList | None = None
        self._line_starts: list[int] = [0]
        self.canvas_rect: canvas.CanvasRect | None = None
        self.canvas_area = canvas.CanvasRect(0, 0, 1, 1)
        self.canvas_anchor = "nw"
        self._drag_edges: set[canvas.Edge] = set()
        self.attach_colors(text, styles)

    def show_canvas(self, rect: canvas.CanvasRect, area: canvas.CanvasRect, anchor: str) -> None:
        """Outline the canvas at `rect`, inside the effect `area`, for a canvas placed by `anchor`."""
        if (rect, area, anchor) != (self.canvas_rect, self.canvas_area, self.canvas_anchor):
            self.canvas_rect = rect
            self.canvas_area = area
            self.canvas_anchor = anchor
            self.refresh()

    def render_line(self, y: int) -> Strip:
        """Render a line with the area outside the canvas dimmed and the canvas outline drawn over it."""
        strip = super().render_line(y)
        rect = self.canvas_rect
        if rect is None:
            return strip
        width = strip.cell_length
        dim = Style(dim=True)
        if rect.top <= y < rect.bottom:
            left = max(0, min(rect.left, width))
            right = max(left, min(rect.right, width))
            before, inside, after = strip.divide([left, right, width])
            strip = Strip.join([_restyle(before, dim), inside, _restyle(after, dim)])
        else:
            strip = _restyle(strip, dim)
        return _draw_outline(strip, y, rect, self.canvas_anchor, _outline_style(self))

    def begin_canvas_drag(self, edges: set[canvas.Edge]) -> None:
        """Start resizing the canvas by dragging `edges`."""
        self._drag_edges = edges
        self.capture_mouse()

    # Textual also runs the `TextArea` mouse handlers after these unless `prevent_default` is called, which keeps
    # a canvas drag from selecting text.

    async def _on_mouse_down(self, event: events.MouseDown) -> None:
        """Start a canvas drag on a movable outline edge. Elsewhere, `TextArea` starts a text selection."""
        if self.canvas_rect is None:
            return
        edges = canvas.edges_at(self.canvas_rect, event.x, event.y, canvas.draggable_edges(self.canvas_anchor))
        if edges:
            event.prevent_default()
            event.stop()
            self.begin_canvas_drag(edges)

    async def _on_mouse_move(self, event: events.MouseMove) -> None:
        """Resize the canvas while dragging an edge. Otherwise, `TextArea` extends the text selection."""
        if not self._drag_edges:
            return
        event.prevent_default()
        width = height = None
        anchor = self.canvas_anchor
        area = self.canvas_area
        if self._drag_edges & {"left", "right"}:
            edge: canvas.Edge = "right" if "right" in self._drag_edges else "left"
            width = canvas.dragged_size(edge, event.x - area.left, area.width, anchor)
        if self._drag_edges & {"top", "bottom"}:
            edge = "bottom" if "bottom" in self._drag_edges else "top"
            height = canvas.dragged_size(edge, event.y - area.top, area.height, anchor)
        self.post_message(ColorTextArea.CanvasResized(width, height))

    async def _on_mouse_up(self, event: events.MouseUp) -> None:
        """Finish a canvas drag. Otherwise, `TextArea` finishes the text selection."""
        if self._drag_edges:
            event.prevent_default()
            self._drag_edges = set()
            self.release_mouse()

    @property
    def color_styles(self) -> colors.StyleList | None:
        """Return the per-character styles of the current text, or `None` when the text has no colors."""
        return self._color_styles

    def attach_colors(self, text: str, styles: colors.StyleList | None) -> None:
        """Attach `styles` to `text`, which must be the editor's current text."""
        self._color_text = text
        self._color_styles = styles if styles and any(styles) else None
        starts = [0]
        starts.extend(index + 1 for index, character in enumerate(text) if character == "\n")
        self._line_starts = starts
        # Rendered lines are cached by the text area, and stale lines lack the new colors.
        line_cache = getattr(self, "_line_cache", None)
        if line_cache is not None:
            line_cache.clear()
        self.refresh()

    def load_colored(self, text: str, styles: colors.StyleList | None) -> None:
        """Replace the editor contents with `text` and its `styles`."""
        self.load_text(text)
        self.attach_colors(text, styles)

    @on(TextArea.Changed)
    def _carry_styles(self) -> None:
        """Keep input colors attached to the characters they belong to after an edit."""
        if self._color_styles is None:
            self._color_text = self.text
            return
        text = self.text
        self.attach_colors(text, colors.carry_styles(self._color_text, self._color_styles, text))

    def colored_text(self) -> str:
        """Return the current text with its input colors as SGR sequences."""
        text = self.text
        if self._color_styles is None or text != self._color_text:
            return text
        return colors.to_ansi(text, self._color_styles)

    def get_line(self, line_index: int) -> Text:
        """Return a line styled with its input colors."""
        line = super().get_line(line_index)
        styles = self._color_styles
        if styles is None or line_index >= len(self._line_starts):
            return line
        start = self._line_starts[line_index]
        for offset in range(len(line.plain)):
            index = start + offset
            if index >= len(styles):
                break
            style = styles[index]
            if style is not None:
                line.stylize(_rich_style(style), offset, offset + 1)
        return line


def _outline_style(widget: Widget) -> Style:
    """Return the style of the canvas outline."""
    return Style(color=widget.app.theme_variables.get("accent", "#fea62b"))


def _draw_outline(strip: Strip, y: int, rect: canvas.CanvasRect, anchor: str, style: Style) -> Strip:
    """Return row `y` of `strip` with the outline of the canvas at `rect` drawn in full blocks.

    The outline is drawn one cell outside the canvas, on the edges that move with `anchor`. Those are the edges the
    effect area leaves room for, so the outline stays visible at any canvas size.
    """
    edges = canvas.draggable_edges(anchor)
    width = strip.cell_length
    if ("top" in edges and y == rect.top - 1) or ("bottom" in edges and y == rect.bottom):
        start = max(0, rect.left - 1 if "left" in edges else rect.left)
        end = min(width, rect.right + 1 if "right" in edges else rect.right)
        if start < end:
            strip = _paint(strip, start, "█" * (end - start), style)
    elif rect.top <= y < rect.bottom:
        for x, edge in ((rect.left - 1, "left"), (rect.right, "right")):
            if edge in edges and 0 <= x < width:
                strip = _paint(strip, x, "█", style)
    return strip


def _restyle(strip: Strip, style: Style) -> Strip:
    """Return `strip` with `style` added on top of each segment's style."""
    return Strip(
        [Segment(text, (segment_style or Style()) + style, control) for text, segment_style, control in strip],
        strip.cell_length,
    )


def _paint(strip: Strip, x: int, text: str, style: Style) -> Strip:
    """Return `strip` with the cells from `x` replaced by `text` in `style`, over the existing background."""
    end = x + len(text)
    before, covered, after = strip.divide([x, end, strip.cell_length])
    background = next((segment.style.bgcolor for segment in covered if segment.style), None)
    return Strip.join([before, Strip([Segment(text, Style(bgcolor=background) + style)], len(text)), after])


def _rich_style(style: colors.CellStyle) -> Style:
    """Return the Rich style for an input color style."""
    return Style(
        color=f"#{style.fg.rgb_color}" if style.fg else None,
        bgcolor=f"#{style.bg.rgb_color}" if style.bg else None,
        bold=style.bold or None,
    )


class CanvasView(Widget, can_focus=True):
    """Shows effect frames over the editor's area."""

    DEFAULT_CSS = """
    CanvasView {
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        """Initialize an empty canvas."""
        super().__init__(**kwargs)
        self._strips: list[Strip] = []
        self.canvas_rect: canvas.CanvasRect | None = None
        self.canvas_area: canvas.CanvasRect | None = None
        self.canvas_anchor = "nw"

    def show_canvas(self, rect: canvas.CanvasRect, area: canvas.CanvasRect, anchor: str) -> None:
        """Place frames in the effect `area` and outline the canvas at `rect`, for a canvas placed by `anchor`."""
        self.canvas_rect = rect
        self.canvas_area = area
        self.canvas_anchor = anchor
        self.refresh()

    def show_frame(self, frame: str) -> None:
        """Display one effect frame."""
        self._strips = frames.frame_to_strips(frame)
        self.refresh()

    def clear(self) -> None:
        """Remove the displayed frame."""
        self._strips = []
        self.refresh()

    def render_line(self, y: int) -> Strip:
        """Return row `y`, with frame rows aligned to the bottom of the effect area as the engine numbers them."""
        width = self.size.width
        area = self.canvas_area or canvas.CanvasRect(0, 0, width, self.size.height)
        index = y - area.top - (area.height - len(self._strips))
        if area.top <= y < area.bottom and 0 <= index < len(self._strips):
            row = self._strips[index].crop_extend(0, area.width, None)
            strip = Strip.join([Strip.blank(area.left), row]).crop_extend(0, width, None)
        else:
            strip = Strip.blank(width)
        if self.canvas_rect is None:
            return strip
        return _draw_outline(strip, y, self.canvas_rect, self.canvas_anchor, _outline_style(self))


class Swatch(Static):
    """Shows a color option's colors and opens the color picker when clicked."""

    class Clicked(Message):
        """Posted when the swatch is clicked."""

    def on_click(self) -> None:
        """Ask the editor to open the color picker."""
        self.post_message(Swatch.Clicked())


class OptionEditor(Horizontal):
    """A labelled input for one option, built from its `ArgSpec`."""

    BINDINGS: typing.ClassVar = [Binding("f7", "pick_color", "Pick color")]

    DEFAULT_CSS = """
    OptionEditor {
        height: 1;
        width: 1fr;
    }
    OptionEditor > .option-label {
        padding: 0 1;
        color: $text-muted;
    }
    OptionEditor.-modified > .option-label {
        color: $text-accent;
    }
    OptionEditor.-invalid > .option-label {
        color: $text-error;
    }
    OptionEditor:focus-within > .option-label {
        text-style: bold;
    }
    OptionEditor:focus-within.-modified > .option-label, OptionEditor:focus-within > .option-label {
        color: $text;
    }
    OptionEditor > Input, OptionEditor > Select, OptionEditor > .swatch, OptionEditor > Checkbox {
        background: $boost;
    }
    OptionEditor > Input, OptionEditor > Select {
        width: 1fr;
    }
    OptionEditor > Input.-textual-compact, OptionEditor > Select.-textual-compact > SelectCurrent {
        padding: 0 1;
    }
    OptionEditor > Input:focus, OptionEditor > Select:focus-within, OptionEditor > Checkbox:focus {
        background: $primary 30%;
    }
    OptionEditor > Input.-invalid {
        color: $text-error;
        background: $error 15%;
    }
    OptionEditor > .swatch {
        width: auto;
        max-width: 8;
        padding: 0 1;
    }
    OptionEditor > Checkbox {
        width: 1fr;
        padding: 0 1;
    }
    """

    class Edited(Message):
        """Posted when the editor's value or validation error changes."""

        def __init__(self, editor: OptionEditor) -> None:
            """Initialize the message for `editor`."""
            super().__init__()
            self.editor = editor

    def __init__(self, scope: str, option: options.OptionField, value: typing.Any, label_width: int = 0) -> None:
        """Initialize an editor for `option` in `scope`, the effect name or the terminal scope.

        A `label_width` above zero sets the label column width, so the inputs of a grid line up.
        """
        super().__init__(id=f"option-{scope}-{option.name}")
        self.scope = scope
        self.label_width = label_width
        self.option = option
        self.value = value
        self.error: str | None = None
        self.tooltip = option.help or None

    def compose(self) -> ComposeResult:
        """Create the label and the widget for the option's kind."""
        option = self.option
        label = Label(option.flag.removeprefix("--"), classes="option-label")
        if self.label_width:
            label.styles.width = self.label_width
        yield label
        if option.kind == "bool":
            yield Checkbox("on" if self.value else "off", value=bool(self.value), compact=True)
        elif option.kind == "choice":
            yield Select(
                [(choice, choice) for choice in option.choices],
                value=option.format(self.value),
                allow_blank=False,
                compact=True,
            )
        else:
            yield Input(option.format(self.value), placeholder=option.format(option.default), compact=True)
            if option.is_color:
                yield Swatch(classes="swatch")

    def on_mount(self) -> None:
        """Show the modified marker and color swatch for the initial value."""
        self._show_state()

    def set_value(self, value: typing.Any) -> None:
        """Replace the editor's value and its widget contents."""
        self.value = value
        self.error = None
        option = self.option
        if option.kind == "bool":
            self.query_one(Checkbox).value = bool(value)
        elif option.kind == "choice":
            self.query_one(Select).value = option.format(value)
        else:
            self.query_one(Input).value = option.format(value)
        self._show_state()

    def _show_state(self) -> None:
        """Mark modified or invalid values and update the color swatch."""
        self.set_class(self.error is None and self.value != self.option.default, "-modified")
        self.set_class(self.error is not None, "-invalid")
        if self.option.kind == "bool":
            self.query_one(Checkbox).label = "on" if self.value else "off"
        if self.option.kind == "text":
            entry = self.query_one(Input)
            entry.set_class(self.error is not None, "-invalid")
            entry.tooltip = self.error or self.option.help or None
        if self.option.is_color:
            swatch = self.query_one(Swatch)
            values = self.value if isinstance(self.value, tuple) else (self.value,)
            text = Text()
            if self.error is None:
                for color in values[:4]:
                    text.append(" ", Style(bgcolor=f"#{color.rgb_color}"))
            text.append(" ▾")
            swatch.update(text)
            swatch.tooltip = "Pick colors (F7, or Enter in the field)"

    @on(Checkbox.Changed)
    def _checkbox_changed(self, event: Checkbox.Changed) -> None:
        event.stop()
        self._accept(event.value)

    @on(Select.Changed)
    def _select_changed(self, event: Select.Changed) -> None:
        event.stop()
        if isinstance(event.value, str):
            self._parse(event.value)

    @on(Input.Changed)
    def _input_changed(self, event: Input.Changed) -> None:
        event.stop()
        self._parse(event.value)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  # noqa: ARG002
        """Offer the color picker only for color options."""
        if action == "pick_color":
            return self.option.is_color
        return True

    @on(Input.Submitted)
    @on(Swatch.Clicked)
    def action_pick_color(self, event: Message | None = None) -> None:
        """Open the color picker with the option's current colors, and apply the colors it returns."""
        if event is not None:
            event.stop()
        if not self.option.is_color:
            return
        current = self.value if isinstance(self.value, tuple) else (self.value,)

        def apply(result: tuple[Color, ...] | None) -> None:
            if result:
                value = result if self.option.is_multi else result[0]
                self.query_one(Input).value = self.option.format(value)

        self.app.push_screen(
            ColorScreen(self.option.flag.removeprefix("--"), current, multiple=self.option.is_multi), apply
        )

    def _parse(self, text: str) -> None:
        try:
            value = self.option.parse(text)
        except ValueError as error:
            self.error = str(error)
            self._show_state()
            self.post_message(OptionEditor.Edited(self))
            return
        self._accept(value)

    def _accept(self, value: typing.Any) -> None:
        self.value = value
        self.error = None
        self._show_state()
        self.post_message(OptionEditor.Edited(self))


class CommandScreen(ModalScreen[None]):
    """Shows the CLI command for the current effect and options."""

    DEFAULT_CSS = """
    CommandScreen {
        align: center middle;
    }
    CommandScreen > Vertical {
        width: 90%;
        height: auto;
        max-height: 80%;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    CommandScreen TextArea {
        height: auto;
        max-height: 12;
        margin: 1 0;
    }
    CommandScreen Horizontal {
        height: auto;
        align-horizontal: right;
    }
    CommandScreen Button {
        margin-left: 1;
    }
    """

    BINDINGS: typing.ClassVar = [Binding("escape", "close", "Close")]

    def __init__(self, command: str) -> None:
        """Initialize the dialog with `command`."""
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        """Create the dialog."""
        with Vertical():
            yield Label("Run this command with your text piped in, or save the text and use --input-file:")
            yield TextArea(self.command, read_only=True, soft_wrap=True, id="command")
            with Horizontal():
                yield Button("Copy", variant="primary", id="copy")
                yield Button("Close", id="close")

    @on(Button.Pressed, "#copy")
    def _copy(self) -> None:
        self.app.copy_to_clipboard(self.command)
        self.app.notify("Command copied to the clipboard.")
        self.dismiss(None)

    @on(Button.Pressed, "#close")
    def action_close(self) -> None:
        """Close the dialog."""
        self.dismiss(None)


class TTEApp(App[None]):
    """Compose text, configure an effect, and play it over the text."""

    TITLE = "TerminalTextEffects"

    CSS = """
    #main {
        height: 1fr;
    }
    #effects {
        width: 24;
        height: 1fr;
        border: round $primary-darken-2;
        border-title-color: $text;
    }
    #effects:focus-within {
        border: round $primary;
    }
    #stage {
        width: 1fr;
        height: 1fr;
        border: round $primary-darken-2;
        border-title-color: $text;
    }
    #stage:focus-within {
        border: round $primary;
    }
    #editor {
        border: none;
        padding: 0;
        height: 1fr;
    }
    #canvas {
        display: none;
    }
    #stage.-playing #editor {
        display: none;
    }
    #stage.-playing #canvas {
        display: block;
    }
    #options {
        height: 16;
        border: round $primary-darken-2;
        border-title-color: $text;
        border-subtitle-color: $text-muted;
        border-subtitle-style: italic;
        border-subtitle-align: left;
    }
    #options:focus-within {
        border: round $primary;
    }
    #options VerticalScroll {
        scrollbar-size-vertical: 1;
        scrollbar-background: $boost;
        scrollbar-color: $primary 40%;
    }
    #options TabPane {
        padding: 0 1;
    }
    .option-grid {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1 3;
        grid-rows: 1;
        height: auto;
    }
    """

    BINDINGS: typing.ClassVar = [
        Binding("f5", "play", "Play", priority=True),
        Binding("escape", "stop", "Stop / edit"),
        Binding("f2", "open", "Open", priority=True),
        Binding("f3", "save", "Save", priority=True),
        Binding("f4", "command", "Command", priority=True),
        Binding("f6", "reset", "Reset options", priority=True),
        Binding("f8", "record", "Record", priority=True),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        effect_resource_map: EffectResourceMap,
        text: str = "",
        input_file: str | None = None,
        effect: str | None = None,
    ) -> None:
        """Initialize the application.

        Args:
            effect_resource_map (EffectResourceMap): Effect command names mapped to their effect and config classes.
            text (str): Initial text, which may contain ANSI colors.
            input_file (str | None): File the text came from, used as the default save path.
            effect (str | None): Effect to select initially.

        """
        super().__init__()
        self.effect_resource_map = dict(sorted(effect_resource_map.items()))
        self.input_file = input_file
        self._file_text: str | None = None
        self._initial_text = text
        self._initial_effect = effect if effect in self.effect_resource_map else None
        self.effect_name = self._initial_effect or next(iter(self.effect_resource_map))
        self._fields: dict[str, list[options.OptionField]] = {}
        self._values: dict[str, dict[str, typing.Any]] = {}
        self._errors: dict[str, dict[str, str]] = {}
        self._iterator: Iterator[str] | None = None
        self._timer: Timer | None = None
        self.state: typing.Literal["editing", "playing", "finished"] = "editing"

    def compose(self) -> ComposeResult:
        """Create the effect list, editor, canvas, and options panel."""
        with Horizontal(id="main"):
            effect_list = OptionList(*self.effect_resource_map, id="effects")
            effect_list.border_title = "Effects"
            yield effect_list
            with Vertical(id="stage"):
                yield ColorTextArea(id="editor")
                yield CanvasView(id="canvas")
        with Vertical(id="options"), TabbedContent():
            with TabPane("Effect", id="effect-tab"), VerticalScroll():
                yield Vertical(id="effect-options", classes="option-grid")
            with TabPane("Canvas", id="canvas-tab"), VerticalScroll():
                yield Vertical(id="terminal-options", classes="option-grid")
        yield Footer()

    async def on_mount(self) -> None:
        """Load the initial text and show the selected effect's options."""
        self.query_one("#stage").border_title = "Text"
        self._load_text(self._initial_text)
        if self.input_file:
            self._file_text = self.editor.text
        terminal_grid = self.query_one("#terminal-options")
        await terminal_grid.mount_all(self._editors(_TERMINAL_SCOPE))
        effect_list = self.query_one("#effects", OptionList)
        effect_list.highlighted = list(self.effect_resource_map).index(self.effect_name)
        await self._show_effect(self.effect_name)
        self.query_one("#editor").focus()

    # Options ---------------------------------------------------------------------------------------------------

    def _scope_fields(self, scope: str) -> list[options.OptionField]:
        """Return the option fields for an effect name or the terminal scope."""
        if scope not in self._fields:
            if scope == _TERMINAL_SCOPE:
                self._fields[scope] = options.option_fields(
                    TerminalConfig,
                    options.TUI_TERMINAL_OPTIONS,
                    options.TUI_TERMINAL_DEFAULTS,
                )
            else:
                self._fields[scope] = options.option_fields(self.effect_resource_map[scope][1])
        return self._fields[scope]

    def _value(self, scope: str, option: options.OptionField) -> typing.Any:
        """Return the current value of `option` in `scope`."""
        return self._values.get(scope, {}).get(option.name, option.default)

    def _scope_values(self, scope: str) -> list[tuple[options.OptionField, typing.Any]]:
        """Return each option in `scope` with its current value."""
        return [(option, self._value(scope, option)) for option in self._scope_fields(scope)]

    def _editors(self, scope: str) -> list[OptionEditor]:
        """Return editors for the options in `scope`, with labels sized to the longest one."""
        fields = self._scope_fields(scope)
        # Each label shows its flag without the leading dashes, padded by one cell on each side.
        label_width = max((len(option.flag) for option in fields), default=0)
        return [OptionEditor(scope, option, self._value(scope, option), label_width) for option in fields]

    async def _show_effect(self, effect_name: str) -> None:
        """Show the options of `effect_name`."""
        self.effect_name = effect_name
        config_class = self.effect_resource_map[effect_name][1]
        parser_spec = getattr(config_class, "parser_spec", None)
        description = getattr(parser_spec, "help", "") or ""
        options_panel = self.query_one("#options")
        options_panel.border_title = f"Options · {effect_name}"
        options_panel.border_subtitle = description
        grid = self.query_one("#effect-options")
        # Editors show each option's last valid value, so errors from an earlier visit no longer apply.
        self._errors.pop(effect_name, None)
        await grid.remove_children()
        await grid.mount_all(self._editors(effect_name))
        self._refresh_subtitle()

    @on(OptionList.OptionHighlighted, "#effects")
    async def _effect_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        name = str(event.option.prompt)
        if name != self.effect_name:
            await self._show_effect(name)

    @on(OptionList.OptionSelected, "#effects")
    def _effect_selected(self) -> None:
        self.action_play()

    @on(OptionEditor.Edited)
    def _option_edited(self, event: OptionEditor.Edited) -> None:
        editor = event.editor
        errors = self._errors.setdefault(editor.scope, {})
        if editor.error is None:
            errors.pop(editor.option.name, None)
            values = self._values.setdefault(editor.scope, {})
            if editor.value == editor.option.default:
                values.pop(editor.option.name, None)
            else:
                values[editor.option.name] = editor.value
            if editor.scope == _TERMINAL_SCOPE and editor.option.name == "tab_width":
                self.editor.indent_width = editor.value
        else:
            errors[editor.option.name] = editor.error
        self._refresh_subtitle()

    def _current_errors(self) -> list[str]:
        """Return validation errors for the selected effect and the terminal options."""
        return [
            f"{name.replace('_', '-')}: {error}"
            for scope in (self.effect_name, _TERMINAL_SCOPE)
            for name, error in self._errors.get(scope, {}).items()
        ]

    def action_reset(self) -> None:
        """Reset the selected effect's options and the canvas options to their defaults."""
        for scope in (self.effect_name, _TERMINAL_SCOPE):
            self._values.pop(scope, None)
            self._errors.pop(scope, None)
        for editor in self.query(OptionEditor):
            editor.set_value(editor.option.default)
        self.notify("Options reset to their defaults.")

    # Text ------------------------------------------------------------------------------------------------------

    @property
    def editor(self) -> ColorTextArea:
        """Return the text editor."""
        return self.query_one("#editor", ColorTextArea)

    def _load_text(self, text: str) -> None:
        """Load `text` into the editor, keeping any ANSI colors as editor styles."""
        styles: colors.StyleList | None = None
        if colors.has_ansi(text):
            try:
                text, styles = colors.parse_colored_text(text, self._tab_width())
            except Exception as error:  # noqa: BLE001
                self.notify(f"Could not read the input colors: {error}", severity="warning")
                text, styles = "".join(ch for ch in text if ch == "\n" or ch.isprintable()), None
        self.editor.indent_width = self._tab_width()
        self.editor.load_colored(text, styles)
        if self.editor.color_styles is not None and self._value_of("existing_color_handling") == "ignore":
            self.notify(
                "Input colors are kept in the text. To use them in effects, set existing color handling on the "
                "Canvas tab to 'always' or 'dynamic'.",
                timeout=8,
            )

    def _value_of(self, terminal_option: str) -> typing.Any:
        """Return the current value of a terminal option."""
        return {option.name: value for option, value in self._scope_values(_TERMINAL_SCOPE)}[terminal_option]

    def _tab_width(self) -> int:
        """Return the configured tab width."""
        return int(self._value_of("tab_width"))

    def action_open(self) -> None:
        """Ask for a file and load its text into the editor."""

        def load(result: tuple[str, bool] | None) -> None:
            if result is None:
                return
            path = Path(result[0]).expanduser()
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                self.notify(f"Cannot open {path}: {error}", severity="error")
                return
            self.action_stop()
            self.input_file = str(path)
            self._load_text(text)
            self._file_text = self.editor.text
            self.notify(f"Opened {path}.")

        self.push_screen(FileScreen("Open text file", self.input_file or "", mode="open"), load)

    def action_save(self) -> None:
        """Ask for a file and save the editor's text to it."""
        has_colors = self.editor.color_styles is not None

        def save(result: tuple[str, bool] | None) -> None:
            if result is None:
                return
            path = Path(result[0]).expanduser()
            text = self.editor.text
            if result[1] and self.editor.color_styles is not None:
                text = colors.to_ansi(text, self.editor.color_styles)
            try:
                path.write_text(text, encoding="utf-8")
            except OSError as error:
                self.notify(f"Cannot save {path}: {error}", severity="error")
                return
            self.input_file = str(path)
            self._file_text = self.editor.text
            self.notify(f"Saved {path}.")

        self.push_screen(
            FileScreen(
                "Save text to file",
                self.input_file or "",
                mode="save",
                checkbox="Keep input colors" if has_colors else None,
                checked=has_colors,
            ),
            save,
        )

    def action_command(self) -> None:
        """Show the CLI command for the selected effect and current options."""
        errors = self._current_errors()
        if errors:
            self.notify("Fix the invalid options first:\n" + "\n".join(errors), severity="error")
            return
        command = options.command_line(
            self.effect_name,
            self._scope_values(self.effect_name),
            self._scope_values(_TERMINAL_SCOPE),
            # A file edited since it was opened or saved no longer holds the previewed text.
            self.input_file if self.editor.text == self._file_text else None,
        )
        self.push_screen(CommandScreen(command))

    # Playback --------------------------------------------------------------------------------------------------

    def _effect_area(self) -> canvas.CanvasRect:
        """Return the part of the text area effects draw in, which leaves room for the canvas outline."""
        size = self.query_one("#stage").content_size
        return canvas.canvas_area(max(1, size.width), max(1, size.height), self._value_of("anchor_canvas"))

    def _canvas_size(self) -> tuple[int, int]:
        """Return the width and height of the area effects are drawn in."""
        area = self._effect_area()
        return area.width, area.height

    def _canvas_geometry(self) -> canvas.CanvasRect:
        """Return where the canvas sits in the text area for the current canvas options."""
        area = self._effect_area()
        values = {option.name: value for option, value in self._scope_values(_TERMINAL_SCOPE)}
        width, height = values["canvas_width"], values["canvas_height"]
        if width < 0 or height < 0:
            # A dimension of -1 follows the text, so let the engine measure it.
            try:
                config = typing.cast("TerminalConfig", options.build_config(TerminalConfig, values))
                terminal = Terminal(self.editor.colored_text(), config, terminal_dimensions=(area.width, area.height))
                width, height = terminal.canvas.width, terminal.canvas.height
            except Exception:  # noqa: BLE001
                width, height = max(width, 0), max(height, 0)
        rect = canvas.canvas_rect(
            area.width,
            area.height,
            width or area.width,
            height or area.height,
            values["anchor_canvas"],
        )
        return canvas.CanvasRect(rect.left + area.left, rect.top + area.top, rect.width, rect.height)

    def _refresh_subtitle(self) -> None:
        """Show the canvas outline, and the canvas size and any validation problem under the text area."""
        area = self._effect_area()
        rect = self._canvas_geometry()
        anchor = self._value_of("anchor_canvas")
        self.editor.show_canvas(rect, area, anchor)
        self.query_one(CanvasView).show_canvas(rect, area, anchor)
        subtitle = f"canvas {rect.width}x{rect.height}"
        if (rect.width, rect.height) != (area.width, area.height):
            subtitle += f" of {area.width}x{area.height}"
        subtitle += " · drag the orange edge to resize"
        errors = self._current_errors()
        if errors:
            subtitle = f"[{len(errors)} invalid option{'s' if len(errors) != 1 else ''}] " + subtitle
        self.query_one("#stage").border_subtitle = subtitle

    @on(TextArea.Changed, "#editor")
    def _text_changed(self) -> None:
        """Update the canvas outline, which can follow the text size."""
        self._refresh_subtitle()

    @on(ColorTextArea.CanvasResized)
    def _canvas_resized(self, event: ColorTextArea.CanvasResized) -> None:
        """Set the canvas options to the size dragged in the text area. A full dimension is stored as 0."""
        area_width, area_height = self._canvas_size()
        for name, value, area in (
            ("canvas_width", event.width, area_width),
            ("canvas_height", event.height, area_height),
        ):
            if value is None:
                continue
            entry = self.query_one(f"#option-{_TERMINAL_SCOPE}-{name}", OptionEditor).query_one(Input)
            text = "0" if value >= area else str(value)
            if entry.value != text:
                entry.value = text

    def on_resize(self, event: Resize) -> None:
        """Fit the option columns to the screen width and update the canvas size shown under the text area."""
        columns = max(1, min(3, event.size.width // _OPTION_COLUMN_WIDTH))
        for grid in self.query(".option-grid"):
            grid.styles.grid_size_columns = columns
        self.call_after_refresh(self._refresh_subtitle)

    def build_effect(self) -> BaseEffect | None:
        """Return the selected effect configured with the current options and text, or `None` if it cannot run."""
        errors = self._current_errors()
        if errors:
            self.notify("Fix the invalid options first:\n" + "\n".join(errors), severity="error")
            return None
        text = self.editor.colored_text()
        if not text.strip():
            self.notify("Type or open some text to play the effect on.", severity="warning")
            return None
        effect_class, config_class = self.effect_resource_map[self.effect_name]
        try:
            effect_config = options.build_config(config_class, dict(self._values.get(self.effect_name, {})))
            terminal_values = {option.name: value for option, value in self._scope_values(_TERMINAL_SCOPE)}
            terminal_config = typing.cast("TerminalConfig", options.build_config(TerminalConfig, terminal_values))
            effect = effect_class(text, effect_config, terminal_config)
        except Exception as error:  # noqa: BLE001
            self.notify(f"Cannot create {self.effect_name}: {error}", severity="error")
            return None
        effect._terminal_dimensions_override = self._canvas_size()
        return effect

    def action_play(self) -> None:
        """Play the selected effect over the text."""
        self._stop_timer()
        effect = self.build_effect()
        if effect is None:
            return
        try:
            self._iterator = iter(effect)
        except Exception as error:  # noqa: BLE001
            self.notify(f"Cannot play {self.effect_name}: {error}", severity="error")
            return
        canvas = self.query_one("#canvas", CanvasView)
        canvas.clear()
        self.query_one("#stage").add_class("-playing")
        self.query_one("#stage").border_title = f"Playing: {self.effect_name}"
        canvas.focus()
        self.state = "playing"
        frame_rate = effect.terminal_config.frame_rate or _MAX_UNLIMITED_FPS
        self._timer = self.set_interval(1 / frame_rate, self._next_frame)
        self.refresh_bindings()

    def _next_frame(self) -> None:
        """Show the next frame, or finish when the effect is complete."""
        if self._iterator is None:
            return
        try:
            frame = next(self._iterator)
        except StopIteration:
            self._finish("Finished")
            return
        except Exception as error:  # noqa: BLE001
            self._finish("Failed")
            self.notify(f"{self.effect_name} failed: {error}", severity="error")
            return
        self.query_one("#canvas", CanvasView).show_frame(frame)

    def _finish(self, label: str) -> None:
        """Stop advancing frames and keep the last frame on screen."""
        self._stop_timer()
        self.state = "finished"
        self.query_one("#stage").border_title = f"{label}: {self.effect_name} (Esc to edit)"
        self.refresh_bindings()

    def _stop_timer(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self._iterator = None

    def action_stop(self) -> None:
        """Stop the effect and return to the text."""
        if self.state == "editing":
            return
        self._stop_timer()
        self.state = "editing"
        stage = self.query_one("#stage")
        stage.remove_class("-playing")
        stage.border_title = "Text"
        self.query_one("#canvas", CanvasView).clear()
        self.editor.focus()
        self.refresh_bindings()

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  # noqa: ARG002
        """Offer Stop only while an effect is shown, and only Quit while a dialog is open."""
        if self.screen.is_modal:
            return action == "quit"
        if action == "stop":
            return self.state != "editing"
        return True

    # Recording -------------------------------------------------------------------------------------------------

    def action_record(self) -> None:
        """Ask for a file and record the selected effect to it."""
        from terminaltexteffects.engine._recording import RECORDING_SUFFIX  # noqa: PLC0415

        if self._value_of("frame_rate") == 0:
            self.notify("Recording needs a frame rate greater than 0 (Canvas tab).", severity="error")
            return

        def record(result: tuple[str, bool] | None) -> None:
            if result is None:
                return
            effect = self.build_effect()
            if effect is not None:
                self._record(effect, self.effect_name, Path(result[0]).expanduser())

        self.push_screen(
            FileScreen("Record effect to file", f"{self.effect_name}{RECORDING_SUFFIX}", mode="save"),
            record,
        )

    @work(thread=True, exclusive=True, group="record")
    def _record(self, effect: BaseEffect, effect_name: str, path: Path) -> None:
        """Render the effect to a recording without displaying it."""
        from terminaltexteffects.__main__ import _record_playbacks  # noqa: PLC0415
        from terminaltexteffects.engine._recording import RecordingError  # noqa: PLC0415

        self.call_from_thread(self.notify, f"Recording {effect_name} to {path}...")
        try:
            header, frame_count, _ = _record_playbacks(path, effect_name, effect, 1)
        except (OSError, RecordingError, ValueError) as error:
            self.call_from_thread(self.notify, f"Recording failed: {error}", severity="error")
            return
        self.call_from_thread(
            self.notify,
            f"Recorded {frame_count} frames ({header.width}x{header.height} at {header.frame_rate} fps) to {path}. "
            f"Play it with: tte --play {path}",
        )
