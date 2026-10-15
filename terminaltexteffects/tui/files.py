"""File dialog for opening, saving, and exporting in the TUI.

The dialog pairs a browsable folder tree with a path field, so files can be picked with the mouse or keyboard, or
typed directly. Opening asks for an existing file, and saving asks before replacing one.
"""

from __future__ import annotations

import typing
from pathlib import Path

from textual import on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, DirectoryTree, Input, Label, Select, Static

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from textual.app import ComposeResult

FileMode = typing.Literal["open", "save"]


class FileFormat(typing.NamedTuple):
    """A file format offered when saving: its label, file suffix, and why it can't be used, if it can't."""

    label: str
    suffix: str
    problem: str | None = None


class FileTree(DirectoryTree):
    """A folder tree that hides dot files unless asked to show them."""

    def __init__(self, path: str | Path, *, id: str | None = None) -> None:  # noqa: A002
        """Initialize the tree at `path` with hidden files hidden."""
        super().__init__(path, id=id)
        self.show_hidden = False

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Return `paths`, without dot files unless hidden files are shown."""
        return [path for path in paths if self.show_hidden or not path.name.startswith(".")]


def _start_folder(path: Path) -> Path:
    """Return the folder to browse first: the folder of `path`, or the working directory."""
    folder = path if path.is_dir() else path.parent
    while not folder.is_dir() and folder != folder.parent:
        folder = folder.parent
    return folder if folder.is_dir() else Path.cwd()


class FileScreen(ModalScreen["tuple[str, bool] | None"]):
    """Asks for a file to open or save, with an optional checkbox.

    Returns the chosen path and the checkbox state, or `None` when cancelled.
    """

    DEFAULT_CSS = """
    FileScreen {
        align: center middle;
    }
    FileScreen > Vertical {
        width: 90%;
        max-width: 100;
        height: 80%;
        border: round $primary;
        border-title-color: $text;
        border-subtitle-color: $text-muted;
        background: $surface;
        padding: 1 2 0 2;
    }
    FileScreen .toolbar, FileScreen .buttons, FileScreen .path-row {
        height: auto;
    }
    FileScreen .toolbar Button {
        width: auto;
        min-width: 8;
        margin-right: 1;
        background: $boost;
    }
    FileScreen #hidden {
        width: auto;
        margin: 0;
        padding: 0 1;
        background: $boost;
    }
    FileScreen #folder {
        width: 1fr;
        color: $text-muted;
        text-overflow: ellipsis;
        text-wrap: nowrap;
        padding-left: 1;
    }
    FileScreen FileTree {
        height: 1fr;
        margin: 1 0;
        background: $boost;
    }
    FileScreen #format {
        width: 14;
        margin-left: 1;
    }
    FileScreen .path-row > Label {
        width: auto;
        padding-right: 1;
        margin-top: 1;
        color: $text-muted;
    }
    FileScreen #path {
        width: 1fr;
        border: tall $primary;
        background: $primary 12%;
        padding: 0 1;
    }
    FileScreen #path:focus {
        border: tall $secondary;
        background: $primary 22%;
    }
    FileScreen #message {
        height: auto;
        color: $text-warning;
    }
    FileScreen #message.-error {
        color: $text-error;
    }
    FileScreen Checkbox {
        margin-top: 1;
    }
    FileScreen .buttons {
        align-horizontal: right;
        margin: 1 0;
    }
    FileScreen .buttons Button {
        margin-left: 1;
    }
    """

    BINDINGS: typing.ClassVar = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+t", "toggle_hidden", "Hidden files"),
        Binding("ctrl+up", "parent", "Parent folder"),
    ]

    def __init__(
        self,
        title: str,
        path: str,
        *,
        mode: FileMode,
        checkbox: str | None = None,
        checked: bool = False,
        formats: Sequence[FileFormat] = (),
    ) -> None:
        """Initialize the dialog.

        Args:
            title (str): Dialog title.
            path (str): Initial path. Its folder is browsed first.
            mode (FileMode): "open" to choose an existing file, or "save" to choose where to write one.
            checkbox (str | None): Label of an optional checkbox shown under the path.
            checked (bool): Initial checkbox state.
            formats (Sequence[FileFormat]): Formats to choose from when saving. Choosing one changes the path's
                suffix, and a format with a `problem` can't be saved.

        """
        super().__init__()
        self._title = title
        self._path = path
        self.mode: FileMode = mode
        self._checkbox = checkbox
        self._checked = checked
        self._formats = tuple(formats)
        self._confirm_path: Path | None = None
        self._last_selected: Path | None = None

    def compose(self) -> ComposeResult:
        """Create the toolbar, folder tree, path field, and buttons."""
        initial = Path(self._path).expanduser() if self._path else Path.cwd()
        folder = _start_folder(initial.resolve() if self._path else initial)
        with Vertical() as dialog:
            dialog.border_title = self._title
            dialog.border_subtitle = "Ctrl+T hidden files · Ctrl+↑ parent folder · Esc cancel"
            with Horizontal(classes="toolbar"):
                yield Button("Home", id="home", compact=True, tooltip="Browse your home folder")
                yield Button("Up", id="up", compact=True, tooltip="Browse the parent folder (Ctrl+↑)")
                yield Static(str(folder), id="folder")
                yield Checkbox("Hidden files", id="hidden", compact=True, tooltip="Show dot files (Ctrl+T)")
            yield FileTree(folder, id="tree")
            with Horizontal(classes="path-row"):
                yield Label("File" if self.mode == "open" else "Save as")
                yield Input(self._path, placeholder="path/to/file", id="path")
                if self._formats:
                    current = self._format_of(self._path)
                    yield Select(
                        [(fmt.label, fmt.suffix) for fmt in self._formats],
                        value=(current or self._formats[0]).suffix,
                        allow_blank=False,
                        id="format",
                    )
            yield Static(id="message")
            if self._checkbox is not None:
                yield Checkbox(self._checkbox, value=self._checked, id="checkbox")
            with Horizontal(classes="buttons"):
                yield Button("Cancel", id="cancel")
                yield Button("Open" if self.mode == "open" else "Save", variant="primary", id="ok")

    def on_mount(self) -> None:
        """Focus the path field."""
        self.query_one("#path", Input).focus()

    @property
    def file_tree(self) -> FileTree:
        """Return the folder tree."""
        return self.query_one(FileTree)

    def _browse(self, folder: Path) -> None:
        """Show `folder` in the tree."""
        self.file_tree.path = folder
        self.query_one("#folder", Static).update(str(folder))

    def _set_message(self, text: str, *, error: bool = False) -> None:
        message = self.query_one("#message", Static)
        message.update(text)
        message.set_class(error, "-error")

    @on(Button.Pressed, "#home")
    def _home(self) -> None:
        self._browse(Path.home())

    @on(Button.Pressed, "#up")
    def action_parent(self) -> None:
        """Browse the parent of the current folder."""
        self._browse(Path(self.file_tree.path).resolve().parent)

    def action_toggle_hidden(self) -> None:
        """Show or hide dot files."""
        self.query_one("#hidden", Checkbox).toggle()

    @on(Checkbox.Changed, "#hidden")
    def _hidden_changed(self, event: Checkbox.Changed) -> None:
        event.stop()
        self.file_tree.show_hidden = event.value
        self.file_tree.reload()

    @on(DirectoryTree.FileSelected)
    def _file_selected(self, event: DirectoryTree.FileSelected) -> None:
        event.stop()
        path = event.path
        self.query_one("#path", Input).value = str(path)
        # Choosing the same file twice in a row, such as a double click, confirms it.
        if path == self._last_selected:
            self._submit()
        self._last_selected = path

    @on(DirectoryTree.DirectorySelected)
    def _directory_selected(self, event: DirectoryTree.DirectorySelected) -> None:
        event.stop()
        if self.mode == "save":
            path_input = self.query_one("#path", Input)
            name = Path(path_input.value).name if path_input.value else ""
            path_input.value = str(event.path / name) if name else f"{event.path}/"

    def _format_of(self, path: str) -> FileFormat | None:
        suffix = Path(path).suffix.lower()
        return next((fmt for fmt in self._formats if fmt.suffix == suffix), None)

    @on(Input.Changed, "#path")
    def _path_changed(self, event: Input.Changed) -> None:
        self._confirm_path = None
        self._set_message("")
        fmt = self._format_of(event.value)
        if fmt is not None:
            select = self.query_one("#format", Select)
            if select.value != fmt.suffix:
                select.value = fmt.suffix
            if fmt.problem:
                self._set_message(fmt.problem)

    @on(Select.Changed, "#format")
    def _format_changed(self, event: Select.Changed) -> None:
        event.stop()
        path_input = self.query_one("#path", Input)
        suffix = str(event.value)
        text = path_input.value
        if Path(text).suffix.lower() == suffix:
            return
        known = self._format_of(text) is not None
        if text and not text.endswith("/"):
            path_input.value = str(Path(text).with_suffix(suffix)) if known else text + suffix

    @on(Input.Submitted, "#path")
    @on(Button.Pressed, "#ok")
    def _submit(self) -> None:
        text = self.query_one("#path", Input).value.strip()
        if not text:
            return
        path = Path(text).expanduser()
        if path.is_dir():
            self._browse(path.resolve())
            return
        if self.mode == "open" and not path.is_file():
            self._set_message(f"{path} is not a file.", error=True)
            return
        if self.mode == "save":
            if not path.parent.is_dir():
                self._set_message(f"Folder {path.parent} does not exist.", error=True)
                return
            if path.exists() and self._confirm_path != path:
                self._confirm_path = path
                self._set_message(f"{path.name} already exists. Press Save again to replace it.")
                return
        fmt = self._format_of(text)
        if fmt is not None and fmt.problem:
            self._set_message(fmt.problem, error=True)
            return
        checked = self.query_one("#checkbox", Checkbox).value if self._checkbox is not None else False
        self.dismiss((text, checked))

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        """Close the dialog without a path."""
        self.dismiss(None)
