"""A panel that stays on screen while an effect is exported, showing what the export is doing."""

from __future__ import annotations

import time
import typing

from textual.containers import Vertical
from textual.widgets import Label, ProgressBar

if typing.TYPE_CHECKING:
    from textual.app import ComposeResult


class ExportProgress(Vertical):
    """An overlay in the bottom-right corner with a busy bar, the frames rendered so far, and the elapsed time.

    The total frame count isn't known until the effect finishes, so the bar is indeterminate. The panel floats
    over the screen, so showing it never changes the layout or the canvas size.
    """

    DEFAULT_CSS = """
    ExportProgress {
        display: none;
        overlay: screen;
        constrain: inside inside;
        dock: bottom;
        offset-x: 100vw;
        margin-bottom: 1;
        width: 44;
        height: auto;
        padding: 0 1;
        border: round $secondary;
        border-title-color: $text;
        background: $surface;
    }
    ExportProgress > ProgressBar {
        width: 100%;
    }
    ExportProgress > ProgressBar > Bar {
        width: 1fr;
    }
    ExportProgress > #export-detail {
        color: $text-muted;
    }
    """

    def __init__(self, **kwargs: typing.Any) -> None:
        """Initialize the hidden panel."""
        super().__init__(**kwargs)
        self._started = 0.0
        self._detail = ""

    def compose(self) -> ComposeResult:
        """Create the bar and the detail line."""
        yield ProgressBar(total=None, show_eta=False, show_percentage=False)
        yield Label(id="export-detail")

    def on_mount(self) -> None:
        """Refresh the elapsed time while the panel is shown."""
        self.set_interval(0.5, self._tick)

    def start(self, effect_name: str) -> None:
        """Show the panel for an export of `effect_name`."""
        self.border_title = f"Exporting {effect_name}"
        self._started = time.monotonic()
        self.display = True
        self._set_detail("Rendering frames…")

    def show_frames(self, count: int) -> None:
        """Show that `count` frames have been rendered."""
        self._set_detail(f"Rendered {count:,} frames")

    def show_rendering(self, format_name: str, frame_count: int) -> None:
        """Show that the `frame_count` rendered frames are being drawn to a `format_name` file."""
        self._set_detail(f"Drawing {frame_count:,} frames to {format_name}")

    def finish(self) -> None:
        """Hide the panel."""
        self.display = False

    def _set_detail(self, detail: str) -> None:
        self._detail = detail
        self._tick()

    def _tick(self) -> None:
        if not self.display:
            return
        elapsed = int(time.monotonic() - self._started)
        self.query_one("#export-detail", Label).update(f"{self._detail} · {elapsed // 60}:{elapsed % 60:02d}")
