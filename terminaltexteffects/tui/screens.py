"""Command and help dialogs for the TUI."""

from __future__ import annotations

import typing

from rich.table import Table
from textual import on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static, TextArea

from terminaltexteffects.tui.theme import gradient_text

if typing.TYPE_CHECKING:
    from textual.app import ComposeResult


class CommandScreen(ModalScreen["str | None"]):
    """Shows the CLI command for the current effect and options, and reads a pasted command.

    Returns a pasted command to load, or `None`.
    """

    DEFAULT_CSS = """
    CommandScreen {
        align: center middle;
    }
    CommandScreen > Vertical {
        width: 90%;
        height: auto;
        max-height: 90%;
        border: round $primary;
        border-title-color: $text;
        background: $surface;
        padding: 1 2;
    }
    CommandScreen TextArea {
        height: auto;
        max-height: 10;
        margin: 1 0;
    }
    CommandScreen .hint {
        color: $text-muted;
    }
    CommandScreen #paste {
        margin: 1 0;
        background: $boost;
        padding: 0 1;
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
        """Initialize the dialog with `command`, or an empty string when the options are invalid."""
        super().__init__()
        self.command = command

    def compose(self) -> ComposeResult:
        """Create the dialog."""
        with Vertical() as dialog:
            dialog.border_title = "Command"
            if self.command:
                yield Label("Run this command with your text piped in, or save the text and use --input-file:")
                yield TextArea(self.command, read_only=True, soft_wrap=True, id="command")
            yield Label("Load a command: paste a tte command to set its effect and options here.", classes="hint")
            yield Input(placeholder="tte decrypt --typing-speed 4", id="paste", compact=True)
            with Horizontal():
                if self.command:
                    yield Button("Copy", id="copy")
                yield Button("Load", variant="primary", id="load")
                yield Button("Close", id="close")

    def on_mount(self) -> None:
        """Focus the paste field when there is no command to copy."""
        if not self.command:
            self.query_one("#paste", Input).focus()

    @on(Button.Pressed, "#copy")
    def _copy(self) -> None:
        self.app.copy_to_clipboard(self.command)
        if getattr(self.app, "copied_to_system_clipboard", False):
            self.app.notify("Command copied to the clipboard.")
        else:
            self.app.notify(
                "Sent the command to the terminal's clipboard. If it isn't there, select it in this dialog and copy.",
                timeout=8,
            )
        self.dismiss(None)

    @on(Input.Submitted, "#paste")
    @on(Button.Pressed, "#load")
    def _load(self) -> None:
        text = self.query_one("#paste", Input).value.strip()
        if text:
            self.dismiss(text)

    @on(Button.Pressed, "#close")
    def action_close(self) -> None:
        """Close the dialog."""
        self.dismiss(None)


KEYS: tuple[tuple[str, str], ...] = (
    ("F1", "Show this help"),
    ("F5", "Play or pause; play again once finished"),
    ("Ctrl+R", "Replay from the start"),
    ("Space / ← →", "Pause or resume / step one frame back or forward, while an effect is shown"),
    ("Esc / click", "Stop the effect and return to the text"),
    ("F9", "Play a random effect"),
    ("F2 / F3", "Open / save the text"),
    ("F4", "Show the command for the current settings, or load a pasted one"),
    ("Ctrl+T / Ctrl+G", "Fit the canvas exactly around the text / grow it to the whole text area"),
    ("Ctrl+B / Ctrl+O", "Hide or show the effect list / the options panel"),
    ("Shift+F6 / F6", "Reset the focused option / all effect and canvas options"),
    ("F7", "Pick colors for the selected color option"),
    ("F8", "Export the effect to a tterec, GIF, or WebP file"),
    ("Tab", "Move between the effect filter, effect list, text, and options"),
    ("Ctrl+P", "Command palette, including themes"),
    ("Ctrl+Q", "Quit"),
)
"""Keys listed on the help screen."""

TIPS = (
    "Drag the canvas outline to resize the canvas. Fit wraps it around the text, and Max fills the text area.",
    "Turn on Auto-replay to replay the effect whenever an option changes, or when you highlight another effect.",
    "Turn on Loop to keep replaying the effect.",
    "Clear an option's field and leave it to return the option to its default.",
    "Right-click the text for a menu with clipboard, color, symbol, and canvas actions.",
    "Type in the filter above the effect list to find an effect by name or description.",
    "Use the bar above the text to color the selection or new text, and Symbols to insert blocks, lines, and arrows.",
    "Select text and click Gradient to spread a gradient across it. Click its arrow to change the gradient.",
    "Run python -m tools.dev --tui to list the effects in dev_effects. Saving one reloads it; red ones cannot play.",
)


class HelpScreen(ModalScreen[None]):
    """Lists the keys and a few tips."""

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    HelpScreen > Vertical {
        width: 84;
        max-width: 100%;
        height: auto;
        max-height: 100%;
        overflow-y: auto;
        border: round $primary;
        background: $surface;
        padding: 1 2;
    }
    HelpScreen #help-title {
        margin-bottom: 1;
    }
    HelpScreen #tips {
        margin-top: 1;
        color: $text-muted;
    }
    HelpScreen Horizontal {
        height: auto;
        align-horizontal: right;
        margin-top: 1;
    }
    """

    BINDINGS: typing.ClassVar = [Binding("escape,f1", "close", "Close")]

    def compose(self) -> ComposeResult:
        """Create the key table and tips."""
        table = Table(box=None, show_header=False, padding=(0, 2, 0, 0))
        table.add_column(style=f"bold {self.app.theme_variables.get('secondary', 'cyan')}", no_wrap=True)
        table.add_column()
        for key, action in KEYS:
            table.add_row(key, action)
        with Vertical():
            yield Static(gradient_text("TerminalTextEffects") + " keys", id="help-title")
            yield Static(table)
            yield Static("\n".join(f"• {tip}" for tip in TIPS), id="tips")
            with Horizontal():
                yield Button("Close", variant="primary", id="close")

    @on(Button.Pressed, "#close")
    def action_close(self) -> None:
        """Close the help."""
        self.dismiss(None)
