"""Textual application for composing text and previewing effects."""

from __future__ import annotations

import typing
from pathlib import Path

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

from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.tui import colors, frames, options

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from textual.events import Resize
    from textual.timer import Timer

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect

    EffectResourceMap = dict[str, tuple[type[BaseEffect], type[BaseConfig]]]

_TERMINAL_SCOPE = "terminal"
_MAX_UNLIMITED_FPS = 120
_OPTION_COLUMN_WIDTH = 64


class ColorTextArea(TextArea):
    """A plain-text editor that shows input colors carried across edits."""

    def __init__(self, text: str = "", styles: colors.StyleList | None = None, **kwargs: typing.Any) -> None:
        """Initialize the editor with `text` and optional per-character `styles`."""
        super().__init__(text, soft_wrap=False, show_line_numbers=False, tab_behavior="focus", **kwargs)
        self._color_text = text
        self._color_styles: colors.StyleList | None = None
        self._line_starts: list[int] = [0]
        self.attach_colors(text, styles)

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

    def show_frame(self, frame: str) -> None:
        """Display one effect frame."""
        self._strips = frames.frame_to_strips(frame)
        self.refresh()

    def clear(self) -> None:
        """Remove the displayed frame."""
        self._strips = []
        self.refresh()

    def render_line(self, y: int) -> Strip:
        """Return row `y`, aligning frame rows to the bottom of the view as the engine numbers them."""
        width = self.size.width
        index = y - (self.size.height - len(self._strips))
        if 0 <= index < len(self._strips):
            return self._strips[index].crop_extend(0, width, None)
        return Strip.blank(width)


class OptionEditor(Horizontal):
    """A labelled input for one option, built from its `ArgSpec`."""

    DEFAULT_CSS = """
    OptionEditor {
        height: 1;
        width: 1fr;
        margin-right: 2;
    }
    OptionEditor > .option-label {
        width: 28;
        color: $text-muted;
    }
    OptionEditor.-modified > .option-label {
        color: $text;
        text-style: bold;
    }
    OptionEditor > Input, OptionEditor > Select {
        width: 1fr;
    }
    OptionEditor > Input.-invalid {
        color: $error;
    }
    OptionEditor > .swatch {
        width: 4;
        margin-left: 1;
    }
    """

    class Edited(Message):
        """Posted when the editor's value or validation error changes."""

        def __init__(self, editor: OptionEditor) -> None:
            """Initialize the message for `editor`."""
            super().__init__()
            self.editor = editor

    def __init__(self, scope: str, option: options.OptionField, value: typing.Any) -> None:
        """Initialize an editor for `option` in `scope`, the effect name or the terminal scope."""
        super().__init__(id=f"option-{scope}-{option.name}")
        self.scope = scope
        self.option = option
        self.value = value
        self.error: str | None = None
        self.tooltip = option.help or None

    def compose(self) -> ComposeResult:
        """Create the label and the widget for the option's kind."""
        option = self.option
        yield Label(option.flag.removeprefix("--"), classes="option-label")
        if option.kind == "bool":
            yield Checkbox(value=bool(self.value), compact=True)
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
                yield Static(classes="swatch")

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
        if self.option.kind == "text":
            entry = self.query_one(Input)
            entry.set_class(self.error is not None, "-invalid")
            entry.tooltip = self.error or self.option.help or None
        if self.option.is_color:
            swatch = self.query_one(".swatch", Static)
            values = self.value if isinstance(self.value, tuple) else (self.value,)
            text = Text()
            if self.error is None:
                for color in values[:4]:
                    text.append(" ", Style(bgcolor=f"#{color.rgb_color}"))
            swatch.update(text)

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


class PathScreen(ModalScreen["tuple[str, bool] | None"]):
    """Asks for a file path, with an optional checkbox."""

    DEFAULT_CSS = """
    PathScreen {
        align: center middle;
    }
    PathScreen > Vertical {
        width: 72;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }
    PathScreen Input {
        margin: 1 0;
    }
    PathScreen Horizontal {
        height: auto;
        align-horizontal: right;
    }
    PathScreen Button {
        margin-left: 1;
    }
    """

    BINDINGS: typing.ClassVar = [Binding("escape", "cancel", "Cancel")]

    def __init__(self, title: str, path: str, checkbox: str | None = None, *, checked: bool = False) -> None:
        """Initialize the dialog with a `title`, an initial `path`, and an optional checkbox label."""
        super().__init__()
        self._title = title
        self._path = path
        self._checkbox = checkbox
        self._checked = checked

    def compose(self) -> ComposeResult:
        """Create the dialog."""
        with Vertical():
            yield Label(self._title)
            yield Input(self._path, placeholder="path/to/file", id="path")
            if self._checkbox is not None:
                yield Checkbox(self._checkbox, value=self._checked, id="checkbox")
            with Horizontal():
                yield Button("OK", variant="primary", id="ok")
                yield Button("Cancel", id="cancel")

    @on(Input.Submitted)
    @on(Button.Pressed, "#ok")
    def _submit(self) -> None:
        path = self.query_one("#path", Input).value.strip()
        if not path:
            return
        checked = self.query_one("#checkbox", Checkbox).value if self._checkbox is not None else False
        self.dismiss((path, checked))

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        """Close the dialog without a path."""
        self.dismiss(None)


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
        height: 14;
        border: round $primary-darken-2;
        border-title-color: $text;
    }
    #options:focus-within {
        border: round $primary;
    }
    #description {
        height: 1;
        color: $text-muted;
        padding: 0 1;
    }
    #options TabPane {
        padding: 0 1;
    }
    .option-grid {
        layout: grid;
        grid-size: 2;
        grid-gutter: 0 1;
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
        with Vertical(id="options"):
            yield Static(id="description")
            with TabbedContent():
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
        await terminal_grid.mount_all(
            OptionEditor(_TERMINAL_SCOPE, option, self._value(_TERMINAL_SCOPE, option))
            for option in self._scope_fields(_TERMINAL_SCOPE)
        )
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

    async def _show_effect(self, effect_name: str) -> None:
        """Show the options of `effect_name`."""
        self.effect_name = effect_name
        config_class = self.effect_resource_map[effect_name][1]
        parser_spec = getattr(config_class, "parser_spec", None)
        description = getattr(parser_spec, "help", "") or ""
        self.query_one("#description", Static).update(Text(f"{effect_name}: {description}"))
        self.query_one("#options").border_title = f"Options: {effect_name}"
        grid = self.query_one("#effect-options")
        # Editors show each option's last valid value, so errors from an earlier visit no longer apply.
        self._errors.pop(effect_name, None)
        await grid.remove_children()
        await grid.mount_all(
            OptionEditor(effect_name, option, self._value(effect_name, option))
            for option in self._scope_fields(effect_name)
        )
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

        self.push_screen(PathScreen("Open text file", self.input_file or ""), load)

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
            PathScreen(
                "Save text to file",
                self.input_file or "",
                "Keep input colors" if has_colors else None,
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

    def _canvas_size(self) -> tuple[int, int]:
        """Return the width and height of the area effects are drawn in."""
        size = self.query_one("#stage").content_size
        return max(1, size.width), max(1, size.height)

    def _refresh_subtitle(self) -> None:
        """Show the canvas size and any validation problem under the text area."""
        width, height = self._canvas_size()
        values = {option.name: value for option, value in self._scope_values(_TERMINAL_SCOPE)}
        canvas_width = values["canvas_width"] if values["canvas_width"] > 0 else width
        canvas_height = values["canvas_height"] if values["canvas_height"] > 0 else height
        subtitle = f"canvas {canvas_width}x{canvas_height}"
        if (canvas_width, canvas_height) != (width, height):
            subtitle += f" of {width}x{height}"
        errors = self._current_errors()
        if errors:
            subtitle = f"[{len(errors)} invalid option{'s' if len(errors) != 1 else ''}] " + subtitle
        self.query_one("#stage").border_subtitle = subtitle

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

        self.push_screen(PathScreen("Record effect to file", f"{self.effect_name}{RECORDING_SUFFIX}"), record)

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
