"""Textual application for composing text and previewing effects."""

from __future__ import annotations

import contextlib
import dataclasses
import functools
import gc
import random
import tempfile
import time
import typing
from collections import deque
from pathlib import Path

from rich.cells import cell_len
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import on, work
from textual.actions import SkipAction
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.geometry import Region
from textual.message import Message
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
from terminaltexteffects.tui import canvas, clipboard, colors, frames, menu, options
from terminaltexteffects.tui.drawer import DrawerHandle
from terminaltexteffects.tui.export_progress import ExportProgress
from terminaltexteffects.tui.files import FileFormat, FileScreen
from terminaltexteffects.tui.gradient import DIRECTIONS, GradientChip, GradientScreen, TextGradient
from terminaltexteffects.tui.picker import ColorScreen
from terminaltexteffects.tui.screens import CommandScreen, HelpScreen
from terminaltexteffects.tui.theme import TTE_THEME, gradient_text
from terminaltexteffects.tui.toolbar import Layer, SymbolScreen, TextToolbar
from terminaltexteffects.utils import export
from terminaltexteffects.utils.graphics import Color

if typing.TYPE_CHECKING:
    from collections.abc import Iterator

    from textual import events
    from textual.events import Resize
    from textual.geometry import Offset
    from textual.timer import Timer

    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect
    from terminaltexteffects.tui.develop import DevEffects

    EffectResourceMap = dict[str, tuple[type[BaseEffect], type[BaseConfig]]]

_TERMINAL_SCOPE = "terminal"
_MAX_UNLIMITED_FPS = 120
_SWATCH_CELL = "  "
"""One color in a clickable swatch: two cells, which look about square in most terminal fonts."""
_MIN_LIST_HEIGHT = 3
"""Fewest rows, borders included, a dropdown list shrinks to when the options panel has little room."""
_CANVAS_LABEL = " CANVAS "
"""Label centered on the canvas outline's bottom edge, or its top edge when only that one moves."""
_OPTION_COLUMN_WIDTH = 64
_STATUS_INTERVAL = 0.25
_LOOP_PAUSE = 1.0
_AUTO_REPLAY_DELAY = 0.35
_PREPARE_POLL = 0.05
_MIN_TICK = 1 / 240
_MAX_KEPT_FRAMES = 2000
"""Longest run, in frames, kept for Loop to replay without building the effect again."""
_MAX_HISTORY_FRAMES = 2000
"""Most frames kept to step back through. Rows that did not change are shared between frames."""
_DEVELOPMENT_POLL = 1.0
"""Seconds between checks of the development effect files for changes."""


class ColorTextArea(TextArea):
    """A plain-text editor that shows input colors carried across edits, and the canvas outline.

    When the canvas is smaller than the editor, cells outside it are dimmed and an outline is drawn just outside it.
    Dragging an outline edge that moves with the canvas anchor resizes the canvas.
    """

    # Terminals that pass Cmd through (with the kitty keyboard protocol) send it as super.
    BINDINGS: typing.ClassVar = [Binding("super+v", "paste", "Paste", show=False)]

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
        self._hover_edges: set[canvas.Edge] = set()
        self._clip: tuple[str, colors.StyleList] | None = None
        """The text last cut or copied here, with its styles, so pasting it back keeps its colors."""
        self._paste_styles: tuple[int, colors.StyleList] | None = None
        """Styles to give a paste in progress, from its start index."""
        self.pen: colors.CellStyle | None = None
        """Style given to typed and inserted text, or `None` to extend the style of the character before.

        An empty `CellStyle` types plain text, even next to colored text.
        """
        self.attach_colors(text, styles)

    def get_component_rich_style(self, *names: str, partial: bool = False, default: Style | None = None) -> Style:
        """Return a component style, with no cursor line style, so text and background colors show on that line."""
        if names == ("text-area--cursor-line",):
            return Style()
        return super().get_component_rich_style(*names, partial=partial, default=default)

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
        hot = self._drag_edges or self._hover_edges
        return _draw_outline(strip, y, rect, self.canvas_anchor, _outline_style(self), hot, _outline_hover_style(self))

    def begin_canvas_drag(self, edges: set[canvas.Edge]) -> None:
        """Start resizing the canvas by dragging `edges`."""
        self._drag_edges = edges
        self.capture_mouse()

    # Textual also runs the `TextArea` mouse handlers after these unless `prevent_default` is called, which keeps
    # a canvas drag from selecting text.

    async def _on_mouse_down(self, event: events.MouseDown) -> None:
        """Open the context menu on a right click, or start a canvas drag on a movable outline edge.

        Elsewhere, `TextArea` starts a text selection.
        """
        if event.button == menu.RIGHT_BUTTON:
            # Keep the selection, so the menu can cut or copy it.
            event.prevent_default()
            event.stop()
            self.post_message(menu.ContextRequested(event.screen_offset))
            return
        if self.canvas_rect is None:
            return
        edges = canvas.edges_at(self.canvas_rect, event.x, event.y, canvas.draggable_edges(self.canvas_anchor))
        if edges:
            event.prevent_default()
            event.stop()
            self.begin_canvas_drag(edges)

    def _set_hover_edges(self, edges: set[canvas.Edge]) -> None:
        if edges != self._hover_edges:
            self._hover_edges = edges
            self.refresh()

    def on_leave(self) -> None:
        """Clear the outline highlight when the mouse leaves the text area."""
        self._set_hover_edges(set())

    async def _on_mouse_move(self, event: events.MouseMove) -> None:
        """Resize the canvas while dragging an edge. Otherwise, light the edges under the mouse.

        `TextArea` then extends any text selection.
        """
        if not self._drag_edges:
            rect = self.canvas_rect
            hover = (
                set()
                if rect is None
                else canvas.edges_at(rect, event.x, event.y, canvas.draggable_edges(self.canvas_anchor))
            )
            self._set_hover_edges(hover)
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
            self.refresh()

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
        """Keep input colors attached to the characters they belong to after an edit, and color new text."""
        if self._color_styles is None and self.pen is None and self._paste_styles is None:
            self._color_text = self.text
            return
        text = self.text
        old_styles: colors.StyleList = self._color_styles or [None] * len(self._color_text)
        styles = colors.carry_styles(self._color_text, old_styles, text, self.pen)
        if self._paste_styles is not None:
            start, pasted = self._paste_styles
            self._paste_styles = None
            styles[start : start + len(pasted)] = pasted[: max(0, len(styles) - start)]
        self.attach_colors(text, styles)

    def _index(self, location: tuple[int, int]) -> int:
        row, column = location
        return self._line_starts[min(row, len(self._line_starts) - 1)] + column

    def paint_gradient(self, gradient: TextGradient) -> bool:
        """Spread `gradient` over the selected characters, and return whether any were selected."""
        start, end = sorted(self.selection)
        if start == end:
            return False
        text = self.text
        styles: colors.StyleList = self._color_styles or [None] * len(text)
        painted = colors.paint_gradient(
            text,
            styles,
            self._index(start),
            self._index(end),
            gradient.build(),
            DIRECTIONS[gradient.direction],
            gradient.layer,
        )
        self.attach_colors(text, painted)
        return True

    def paint_selection(self, update: typing.Callable[[colors.CellStyle | None], colors.CellStyle | None]) -> bool:
        """Apply `update` to the styles of the selected characters, and return whether any were selected."""
        start, end = sorted(self.selection)
        if start == end:
            return False
        text = self.text
        styles: colors.StyleList = self._color_styles or [None] * len(text)
        self.attach_colors(text, colors.paint(text, styles, self._index(start), self._index(end), update))
        return True

    def _remember_clip(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        """Keep the text from `start` to `end` with its styles, for a later paste."""
        text = self.get_text_range(start, end)
        styles = self._color_styles
        if styles is None or text != self._color_text[self._index(start) : self._index(end)]:
            self._clip = None
            return
        self._clip = (text, styles[self._index(start) : self._index(end)])

    def _expect_paste(self, text: str) -> None:
        """Give `text` the styles it was cut or copied with, if it is the text last cut or copied here."""
        if self._clip is not None and self._clip[0] == text and any(self._clip[1]):
            self._paste_styles = (self._index(min(self.selection)), self._clip[1])

    def action_copy(self) -> None:
        """Copy the selection, keeping its colors for pasting here."""
        start, end = sorted(self.selection)
        if start != end:
            self._remember_clip(start, end)
        super().action_copy()

    def action_cut(self) -> None:
        """Cut the selection, or the cursor line, keeping its colors for pasting here."""
        start, end = sorted(self.selection)
        if start == end:
            row = start[0]
            # Without a selection, `TextArea` cuts the whole cursor line with its line break.
            start, end = (row, 0), (row + 1, 0) if row + 1 < self.document.line_count else self.document.end
        self._remember_clip(start, end)
        super().action_cut()

    def action_paste(self) -> None:
        """Paste the system clipboard, or the app's own clipboard when the system clipboard can't be read."""
        if self.read_only:
            return
        text = clipboard.paste_with_system_command()
        if text is None:
            text = self.app.clipboard
        self._expect_paste(text)
        if result := self._replace_via_keyboard(text, *self.selection):
            self.move_cursor(result.end_location)
        else:
            self._paste_styles = None

    async def _on_paste(self, event: events.Paste) -> None:
        """Keep the colors of pasted text that was cut or copied here.

        Textual then runs the `TextArea` handler, which inserts the text.
        """
        if not self.read_only:
            self._expect_paste(event.text)

    def insert_symbol(self, symbol: str) -> None:
        """Replace the selection with `symbol`, as typing it would, and place the cursor after it."""
        start, end = sorted(self.selection)
        result = self.replace(symbol, start, end, maintain_selection_offset=False)
        self.move_cursor(result.end_location)

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


def _outline_hover_style(widget: Widget) -> Style:
    """Return the style of the outline edges under the mouse or being dragged."""
    return Style(color=widget.app.theme_variables.get("foreground", "#ffffff"))


def _draw_outline(
    strip: Strip,
    y: int,
    rect: canvas.CanvasRect,
    anchor: str,
    style: Style,
    hot: typing.AbstractSet[canvas.Edge] = frozenset(),
    hot_style: Style | None = None,
) -> Strip:
    """Return row `y` of `strip` with the outline of the canvas at `rect` drawn in full blocks.

    The outline is drawn one cell outside the canvas, on the edges that move with `anchor`. Those are the edges the
    effect area leaves room for, so the outline stays visible at any canvas size. The `hot` edges, under the mouse
    or being dragged, are drawn in `hot_style`. The bottom edge, or the top edge when the bottom doesn't move, is
    labeled `CANVAS` in its center.
    """
    edges = canvas.draggable_edges(anchor)
    width = strip.cell_length
    hot_style = hot_style or style
    side_styles = {edge: hot_style if edge in hot else style for edge in ("left", "right")}
    if ("top" in edges and y == rect.top - 1) or ("bottom" in edges and y == rect.bottom):
        edge: canvas.Edge = "top" if "top" in edges and y == rect.top - 1 else "bottom"
        row_style = hot_style if edge in hot else style
        start = rect.left - 1 if "left" in edges else rect.left
        end = rect.right + 1 if "right" in edges else rect.right
        cells = [(x, row_style) for x in range(start, end)]
        if edge not in hot:
            # A hot side edge lights its corners too, so the edge reads as one piece.
            cells = [
                (x, side_styles["left"] if x == rect.left - 1 else side_styles["right"] if x == rect.right else s)
                for x, s in cells
            ]
        for x, cell_style in cells:
            if 0 <= x < width:
                strip = _paint(strip, x, "█", cell_style)
        labeled = "bottom" if "bottom" in edges else "top"
        if edge == labeled and rect.width >= len(_CANVAS_LABEL) + 2:
            x = rect.left + (rect.width - len(_CANVAS_LABEL)) // 2
            if x >= 0 and x + len(_CANVAS_LABEL) <= width:
                # Dark letters on the outline's color, so the label reads as cut out of the edge.
                strip = _paint(strip, x, _CANVAS_LABEL, Style(color="black", bgcolor=row_style.color, bold=True))
    elif rect.top <= y < rect.bottom:
        for x, side in ((rect.left - 1, "left"), (rect.right, "right")):
            if side in edges and 0 <= x < width:
                strip = _paint(strip, x, "█", side_styles[side])
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

    BINDINGS: typing.ClassVar = [
        Binding("space", "app.play", "Pause/Resume"),
        Binding("left", "app.step_back", "Back"),
        Binding("right", "app.step", "Step"),
    ]

    DEFAULT_CSS = """
    CanvasView {
        width: 1fr;
        height: 1fr;
    }
    """

    class Clicked(Message):
        """Posted when the canvas is clicked, to return to the text at the clicked cell."""

        def __init__(self, event: events.Click) -> None:
            """Initialize the message with the click `event`."""
            super().__init__()
            self.event = event

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Open the context menu on a right click."""
        if event.button == menu.RIGHT_BUTTON:
            event.stop()
            self.post_message(menu.ContextRequested(event.screen_offset))

    def on_click(self, event: events.Click) -> None:
        """Ask the app to stop the effect and return to the text."""
        event.stop()
        if event.button == menu.RIGHT_BUTTON:
            return
        self.post_message(CanvasView.Clicked(event))

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
        self.show_strips(frames.frame_to_strips(frame))

    def show_strips(self, strips: frames.Frame) -> None:
        """Display one frame converted to strips, redrawing only the rows that changed since the last frame.

        Rows that did not change share their `Strip` with the previous frame, so a changed row is one whose strip is
        a different object.
        """
        previous = self._strips
        self._strips = strips
        if len(previous) != len(strips) or self.canvas_area is None:
            self.refresh()
            return
        width = self.size.width
        top = self.canvas_area.top + self.canvas_area.height - len(strips)
        start: int | None = None
        for index in range(len(strips) + 1):
            changed = index < len(strips) and strips[index] is not previous[index]
            if changed and start is None:
                start = index
            elif not changed and start is not None:
                self.refresh(Region(0, top + start, width, index - start))
                start = None

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


class PanelSelect(Select[str]):
    """A `Select` whose list stays inside the scrolling panel that holds it, scrolling instead of overflowing.

    The list opens below the field when it fits there or there is more room below, and above the field otherwise.
    """

    def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None:
        """Initialize the select, with no tooltips hidden yet."""
        super().__init__(*args, **kwargs)
        self._hidden_tooltips: list[tuple[Widget, typing.Any]] = []

    def _watch_expanded(self, expanded: bool) -> None:  # noqa: FBT001 (Textual calls watchers positionally)
        if expanded:
            self._fit_overlay()
            self._hide_tooltips()
        else:
            self._restore_tooltips()
        super()._watch_expanded(expanded)

    def _hide_tooltips(self) -> None:
        """Hide the tooltips of the select's ancestors, which would otherwise cover the open list."""
        for node in self.ancestors_with_self:
            if isinstance(node, Widget) and node.tooltip is not None:
                self._hidden_tooltips.append((node, node.tooltip))
                node.tooltip = None

    def _restore_tooltips(self) -> None:
        for node, tooltip in self._hidden_tooltips:
            if node.tooltip is None:
                node.tooltip = tooltip
        self._hidden_tooltips.clear()

    def _fit_overlay(self) -> None:
        panel = next((ancestor for ancestor in self.ancestors if isinstance(ancestor, VerticalScroll)), None)
        if panel is None:
            return
        overlay = self.query_one("SelectOverlay", OptionList)
        bounds = panel.region
        top = self.region.y
        # The list has a border row above and below its options.
        wanted = overlay.option_count + 2
        below = bounds.bottom - (top + 1)
        above = top - bounds.y
        if wanted <= below or below >= above:
            overlay.styles.max_height = max(below, _MIN_LIST_HEIGHT)
            overlay.styles.offset = (0, 0)
        else:
            height = max(min(wanted, above), _MIN_LIST_HEIGHT)
            overlay.styles.max_height = height
            overlay.styles.offset = (0, -(height + 1))


class OptionEditor(Horizontal):
    """A labelled input for one option, built from its `ArgSpec`."""

    BINDINGS: typing.ClassVar = [
        Binding("f7", "pick_color", "Pick color"),
        Binding("shift+f6", "reset_option", "Default"),
    ]

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
        max-width: 14;
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
        self.tooltip = self._option_tooltip()

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
            yield PanelSelect(
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

    def _option_tooltip(self) -> str | None:
        """Return the option's help, value format, example, and default, led by any validation error."""
        option = self.option
        parts = [option.help, option.format_hint()]
        if option.kind == "text":
            parts.append(f"Default: {option.format(option.default) or '(empty)'}")
        text = "\n\n".join(part for part in parts if part)
        if self.error:
            text = f"{self.error}\n\n{text}" if text else self.error
        return text or None

    def _show_state(self) -> None:
        """Mark modified or invalid values and update the color swatch."""
        self.set_class(self.error is None and self.value != self.option.default, "-modified")
        self.set_class(self.error is not None, "-invalid")
        if self.option.kind == "bool":
            self.query_one(Checkbox).label = "on" if self.value else "off"
        if self.option.kind == "text":
            entry = self.query_one(Input)
            entry.set_class(self.error is not None, "-invalid")
            entry.tooltip = self._option_tooltip()
        if self.option.is_color:
            swatch = self.query_one(Swatch)
            values = self.value if isinstance(self.value, tuple) else (self.value,)
            text = Text()
            if self.error is None:
                for color in values[:4]:
                    text.append(_SWATCH_CELL, Style(bgcolor=f"#{color.rgb_color}"))
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

    @on(Input.Blurred)
    def _input_blurred(self, event: Input.Blurred) -> None:
        """Return a field left blank to the option's default."""
        event.stop()
        if not event.value.strip():
            self.action_reset_option()

    def action_reset_option(self) -> None:
        """Return this option to its default."""
        self.set_value(self.option.default)
        self.post_message(OptionEditor.Edited(self))

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


class EffectFilter(Input):
    """Filters the effect list. Down or Enter moves to the list."""

    BINDINGS: typing.ClassVar = [Binding("down", "app.focus_effects", "Effects", show=False)]


class TTEApp(App[None]):
    """Compose text, configure an effect, and play it over the text."""

    TITLE = "TerminalTextEffects"

    CSS = """
    #header {
        height: 1;
        padding: 0 1;
    }
    #title {
        width: 1fr;
    }
    #hint {
        width: auto;
        color: $text-muted;
    }
    #main {
        height: 1fr;
    }
    #effects-panel {
        width: 17;
        height: 1fr;
        border: round $primary;
        /* The drawer handle beside the panel stands in for its right border. */
        border-right: none;
        border-title-color: $text;
    }
    #effects-panel:focus-within {
        border: round $secondary;
        border-right: none;
    }
    #effect-filter {
        background: $boost;
        padding: 0 1;
        margin-bottom: 1;
    }
    #effect-filter:focus {
        background: $primary 30%;
    }
    #effects {
        height: 1fr;
        scrollbar-size-vertical: 1;
        border: none;
        padding: 0;
        background: transparent;
    }
    #right {
        width: 1fr;
        height: 1fr;
    }
    #transport {
        height: 1;
        padding: 0;
    }
    #transport #max, #transport #auto-replay {
        margin-right: 0;
    }
    #transport Button {
        margin-right: 1;
        min-width: 0;
    }
    #transport-gap {
        width: 1fr;
        min-width: 1;
    }
    #transport #play {
        width: 10;
    }
    #transport Checkbox {
        margin-right: 1;
        padding: 0;
        background: $boost;
    }
    #transport Checkbox:focus {
        background: $primary 30%;
    }
    #stage {
        width: 1fr;
        height: 1fr;
        border: round $primary;
        border-title-color: $text;
    }
    #stage:focus-within {
        border: round $secondary;
    }
    #editor {
        border: none;
        padding: 0;
        height: 1fr;
        /* Scrollbars would cover the canvas outline at the text area's edges. The text still scrolls. */
        scrollbar-size: 0 0;
    }
    #canvas {
        display: none;
    }
    #stage.-playing #editor {
        display: none;
    }
    #stage.-playing {
        background: #000000;
    }
    #stage.-playing #canvas {
        display: block;
        background: #000000;
    }
    #import-error {
        display: none;
        height: 1fr;
        padding: 0 1;
        color: $error;
        scrollbar-size-vertical: 1;
    }
    #stage.-import-error #editor {
        display: none;
    }
    #stage.-import-error #import-error {
        display: block;
    }
    #options {
        height: 16;
        border: round $primary;
        border-title-color: $text;
        border-subtitle-color: $text-muted;
        border-subtitle-style: italic;
        border-subtitle-align: left;
    }
    #options:focus-within {
        border: round $secondary;
    }
    #options VerticalScroll {
        scrollbar-size-vertical: 1;
        scrollbar-background: $boost;
        scrollbar-color: $primary 60%;
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
    /* Every control lightens under the mouse, over whatever color its state gives it. */
    Button:enabled:hover, Button.-primary:enabled:hover {
        background: $primary;
        background-tint: $foreground 25%;
        color: $text;
    }
    Checkbox:hover, #transport Checkbox:hover, OptionEditor > Checkbox:hover, SelectCurrent:hover, Tab:hover {
        background-tint: $foreground 25%;
    }
    /* Text fields are transparent, which a tint can't lighten, so they get a background. */
    Input:hover, OptionEditor > Input:hover, #effect-filter:hover {
        background: $primary 45%;
    }
    /* A tint would barely show around the color cells, so the swatch's padding turns solid purple. */
    OptionEditor > .swatch:hover {
        background: $primary;
    }
    OptionEditor > Input.-invalid:hover {
        background: $error 35%;
    }
    Checkbox:hover > .toggle--label {
        background: $primary;
        color: $text;
    }
    """

    BINDINGS: typing.ClassVar = [
        Binding("f1", "help", "Help", priority=True),
        Binding("f5", "play", "Play/Pause", priority=True),
        Binding("ctrl+r", "replay", "Replay", priority=True, show=False),
        Binding("f9", "random", "Random effect", priority=True, show=False),
        Binding("ctrl+t", "fit_canvas", "Fit canvas", priority=True, show=False),
        Binding("ctrl+g", "maximize_canvas", "Maximize canvas", priority=True, show=False),
        Binding("escape", "stop", "Stop / edit"),
        Binding("f2", "open", "Open", priority=True),
        Binding("f3", "save", "Save", priority=True),
        Binding("f4", "command", "Command", priority=True),
        Binding("f6", "reset", "Reset options", priority=True, show=False),
        Binding("f8", "export", "Export", priority=True),
        Binding("ctrl+b", "toggle_panel('effects-drawer')", "Effect list", priority=True, show=False),
        Binding("ctrl+o", "toggle_panel('options-drawer')", "Options panel", priority=True, show=False),
        Binding("ctrl+q", "quit", "Quit", priority=True),
    ]

    def __init__(
        self,
        effect_resource_map: EffectResourceMap,
        text: str = "",
        input_file: str | None = None,
        effect: str | None = None,
        development: DevEffects | None = None,
    ) -> None:
        """Initialize the application.

        Args:
            effect_resource_map (EffectResourceMap): Effect command names mapped to their effect and config classes.
            text (str): Initial text, which may contain ANSI colors.
            input_file (str | None): File the text came from, used as the default save path.
            effect (str | None): Effect to select initially.
            development (DevEffects | None): Watched effect modules, listed with the others and imported again when
                their files change. Modules that cannot be played are listed in red.

        """
        super().__init__()
        self._fixed_effects = dict(effect_resource_map)
        self._development = development
        self.effect_resource_map: EffectResourceMap = {}
        self._broken: dict[str, str] = {}
        """File names of development effects that cannot be played, with the reason."""
        if development is not None:
            development.scan()
        self._collect_effects()
        self.input_file = input_file
        self._file_text: str | None = None
        self._initial_text = text
        names = self._effect_names()
        self._initial_effect = effect if effect in names else None
        self.effect_name = self._initial_effect or next(iter(self.effect_resource_map), names[0])
        self._listed = names
        self._fields: dict[str, list[options.OptionField]] = {}
        self._values: dict[str, dict[str, typing.Any]] = {}
        self._errors: dict[str, dict[str, str]] = {}
        self._stream: frames.FrameStream | frames.RecordedFrames | None = None
        self._timer: Timer | None = None
        self._loop_timer: Timer | None = None
        self._auto_timer: Timer | None = None
        self._frame_rate = _MAX_UNLIMITED_FPS
        self._due = 0.0
        self._canvas_note = ""
        self._frame_index = 0
        self._shown_at: deque[float] = deque(maxlen=_MAX_UNLIMITED_FPS * 2)
        self._recording: list[frames.Frame] | None = None
        self._history: deque[frames.Frame] = deque(maxlen=_MAX_HISTORY_FRAMES)
        """The frames shown in this run, newest last, to step back through."""
        self._back = 0
        """How many frames before the newest one in `_history` is on screen."""
        self._playback_key: tuple[typing.Any, ...] | None = None
        self._recorded: tuple[tuple[typing.Any, ...], list[frames.Frame]] | None = None
        self._reloads = 0
        """How many times effect modules were imported again, so frames recorded before a reload are not reused."""
        self._color_hint_shown = False
        self._gradient = TextGradient()
        """Gradient the toolbar's gradient chip applies to the selection."""
        self.copied_to_system_clipboard = False
        self._export_suffix = export.FORMATS[0].suffix
        self.state: typing.Literal["editing", "playing", "paused", "finished"] = "editing"
        self.register_theme(TTE_THEME)
        self.theme = TTE_THEME.name

    def compose(self) -> ComposeResult:
        """Create the header, effect list, playback bar, editor, canvas, and options panel."""
        with Horizontal(id="header"):
            yield Static(gradient_text("TerminalTextEffects"), id="title")
            yield Static("F1 help", id="hint")
        with Horizontal(id="main"):
            with Vertical(id="effects-panel") as effects_panel:
                effects_panel.border_title = "Effects"
                yield EffectFilter(placeholder="Filter effects", id="effect-filter", compact=True)
                yield OptionList(*self._prompts(self._listed), id="effects")
            yield DrawerHandle("left", "Effect list", "Ctrl+B", id="effects-drawer")
            with Vertical(id="right"):
                with Horizontal(id="transport"):
                    yield from self._transport_buttons(
                        ("▶ Play", "play", "Play or pause, or play again from the start (F5)"),
                        ("■ Stop", "stop", "Stop and return to the text (Esc)"),
                        ("←", "step_back", "Step back: pause, then show the frame before (←)"),
                        ("→", "step", "Step: pause, then show the next frame (→)"),
                        ("Random", "random", "Play a random effect (F9)"),
                    )
                    yield Checkbox("Loop", id="loop", compact=True)
                    yield Checkbox("Auto", id="auto-replay", compact=True)
                    yield Static(id="transport-gap")
                    yield from self._transport_buttons(
                        ("Open", "open", "Open a text file (F2)"),
                        ("Save", "save", "Save the text to a file (F3)"),
                        ("Export", "export", "Export the effect as a tterec, GIF, or WebP file (F8)"),
                    )
                    yield from self._transport_buttons(
                        ("Fit", "fit", "Fit the canvas exactly around the text (Ctrl+T)"),
                        ("Max", "max", "Grow the canvas to the whole text area (Ctrl+G)"),
                    )
                yield TextToolbar(id="text-tools")
                with Vertical(id="stage"):
                    yield ColorTextArea(id="editor")
                    yield CanvasView(id="canvas")
                    with VerticalScroll(id="import-error"):
                        yield Static(id="import-error-text", markup=False)
        yield DrawerHandle("bottom", "Options", "Ctrl+O", id="options-drawer")
        with Vertical(id="options"), TabbedContent():
            with TabPane("Effect", id="effect-tab"), VerticalScroll():
                yield Vertical(id="effect-options", classes="option-grid")
            with TabPane("Canvas", id="canvas-tab"), VerticalScroll():
                yield Vertical(id="terminal-options", classes="option-grid")
        yield ExportProgress(id="export-progress")
        yield Footer()

    @staticmethod
    def _transport_buttons(*buttons: tuple[str, str, str]) -> Iterator[Button]:
        for label, button_id, tooltip in buttons:
            button = Button(label, id=button_id, compact=True, variant="primary")
            button.can_focus = False
            button.tooltip = tooltip
            yield button

    async def on_mount(self) -> None:
        """Load the initial text and show the selected effect's options."""
        self.query_one("#stage").border_title = "Text"
        self.query_one("#loop", Checkbox).tooltip = "Replay the effect when it finishes"
        self.query_one(
            "#auto-replay", Checkbox
        ).tooltip = "Replay the effect when an option changes, another effect is highlighted, or its file changes"
        self._load_text(self._initial_text)
        if self.input_file:
            self._file_text = self.editor.text
        terminal_grid = self.query_one("#terminal-options")
        await terminal_grid.mount_all(self._editors(_TERMINAL_SCOPE))
        effect_list = self.query_one("#effects", OptionList)
        effect_list.highlighted = self._listed.index(self.effect_name)
        await self._show_effect(self.effect_name)
        self._update_transport()
        self.query_one("#stage").set_interval(_STATUS_INTERVAL, self._update_status)
        if self._development is not None:
            self.query_one("#effects").set_interval(_DEVELOPMENT_POLL, self._check_development)
        self.query_one("#editor").focus()

    async def action_quit(self) -> None:
        """Stop playback and quit."""
        self._cancel_playback()
        self.exit()

    # Effects list ----------------------------------------------------------------------------------------------

    def _collect_effects(self) -> None:
        """Gather the playable effects, and the development effects that cannot be played."""
        effects = dict(self._fixed_effects)
        self._broken = {}
        if self._development is not None:
            effects.update(self._development.playable())
            self._broken = self._development.broken()
        self.effect_resource_map = dict(sorted(effects.items()))

    def _effect_names(self) -> list[str]:
        """Return the names of every listed effect, including development effects that cannot be played."""
        return sorted([*self.effect_resource_map, *self._broken])

    def _prompts(self, names: list[str]) -> list[str | Text]:
        """Return the effect list entries for `names`, in red for effects that cannot be played."""
        error_color = TTE_THEME.error or "red"
        return [Text(name, style=error_color) if name in self._broken else name for name in names]

    def _description(self, effect_name: str) -> str:
        """Return the description of `effect_name` from its parser spec, or why it cannot be played."""
        if effect_name in self._broken:
            return "Cannot be played: " + self._broken[effect_name].splitlines()[-1]
        parser_spec = getattr(self.effect_resource_map[effect_name][1], "parser_spec", None)
        return getattr(parser_spec, "help", "") or ""

    @on(Input.Changed, "#effect-filter")
    def _filter_changed(self, event: Input.Changed) -> None:
        """List the effects whose name or description contains every word of the filter."""
        self._list_effects(event.value)

    def _list_effects(self, effect_filter: str, *, force: bool = False) -> None:
        """List the effects whose name or description contains every word of `effect_filter`.

        The list is rebuilt only when the listed names change, unless `force` is set.
        """
        listed = self._filtered(effect_filter)
        if listed == self._listed and not force:
            return
        self._listed = listed
        effect_list = self.query_one("#effects", OptionList)
        effect_list.clear_options()
        effect_list.add_options(self._prompts(listed))
        if listed:
            effect_list.highlighted = listed.index(self.effect_name) if self.effect_name in listed else 0

    def _filtered(self, effect_filter: str) -> list[str]:
        """Return the effects whose name or description contains every word of `effect_filter`."""
        words = effect_filter.lower().split()
        return [
            name
            for name in self._effect_names()
            if all(word in f"{name} {self._description(name)}".lower() for word in words)
        ]

    @on(Input.Submitted, "#effect-filter")
    def action_focus_effects(self) -> None:
        """Move focus to the effect list."""
        self.query_one("#effects", OptionList).focus()

    def _clear_filter(self) -> None:
        """Show every effect again."""
        effect_filter = self.query_one("#effect-filter", Input)
        if effect_filter.value:
            effect_filter.value = ""
        self._listed = self._effect_names()
        effect_list = self.query_one("#effects", OptionList)
        effect_list.clear_options()
        effect_list.add_options(self._prompts(self._listed))

    def _highlight_effect(self, effect_name: str) -> None:
        """Highlight `effect_name` in the effect list, clearing a filter that hides it."""
        if effect_name not in self._listed:
            self._clear_filter()
        self.query_one("#effects", OptionList).highlighted = self._listed.index(effect_name)

    @on(OptionList.OptionHighlighted, "#effects")
    async def _effect_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        name = str(event.option.prompt)
        if name != self.effect_name:
            await self._show_effect(name)
            self._schedule_auto_replay()

    @on(OptionList.OptionSelected, "#effects")
    def _effect_selected(self) -> None:
        self.start_playback()

    async def action_random(self) -> None:
        """Select and play a random effect from the listed effects, or from all effects if fewer are listed."""
        candidates = [name for name in self._listed if name != self.effect_name and name not in self._broken]
        if not candidates:
            candidates = [name for name in self.effect_resource_map if name != self.effect_name]
        if not candidates:
            return
        name = random.choice(candidates)
        await self._show_effect(name)
        self._highlight_effect(name)
        self.start_playback()

    # Development effects ---------------------------------------------------------------------------------------

    async def _check_development(self) -> None:
        """Import the development effects whose files changed, and list them again.

        When the selected effect changed, the options it still has keep their values, and it replays while
        Auto-replay is on.
        """
        development = self._development
        # Widgets are rebuilt below, which waits until the main screen is shown again.
        if development is None or self.screen.is_modal:
            return
        changed = development.scan()
        if not changed:
            return
        selected: Path | None = None
        for path, old_name in changed.items():
            effect = development.effects.get(path)
            new_name = None if effect is None else effect.name
            for name in (old_name, new_name):
                if name is not None:
                    self._fields.pop(name, None)
                    self._errors.pop(name, None)
            if old_name is not None and new_name is not None and old_name != new_name and old_name in self._values:
                self._values[new_name] = self._values.pop(old_name)
            if old_name == self.effect_name:
                selected = path
        self._collect_effects()
        for scope in [scope for scope in self._values if scope in self.effect_resource_map]:
            kept = {option.name for option in self._scope_fields(scope)}
            self._values[scope] = {name: value for name, value in self._values[scope].items() if name in kept}
        self._recorded = None
        self._reloads += 1
        names = self._effect_names()
        if selected is not None or self.effect_name not in names:
            effect = None if selected is None else development.effects.get(selected)
            if effect is None:
                self.action_stop()
            name = effect.name if effect is not None else next(iter(self.effect_resource_map), names[0])
            await self._show_effect(name)
        effect_filter = self.query_one("#effect-filter", Input)
        if self.effect_name not in self._filtered(effect_filter.value):
            effect_filter.value = ""
        self._list_effects(effect_filter.value, force=True)
        if selected is None or selected not in development.effects:
            return
        if self.effect_name in self._broken:
            self.notify(f"{self.effect_name} cannot be played.", severity="error")
        else:
            self.notify(f"Reloaded {self.effect_name}.")
        if self.query_one("#auto-replay", Checkbox).value:
            self._schedule_auto_replay()
        elif self.query_one("#stage").has_class("-import-error"):
            if self.effect_name in self._broken:
                self._show_import_error()
            else:
                self.action_stop()

    def _show_import_error(self) -> None:
        """Show why the selected development effect cannot be played, in place of the text."""
        self._cancel_playback()
        self._recording = None
        self._history.clear()
        self._back = 0
        stage = self.query_one("#stage")
        stage.remove_class("-playing")
        stage.add_class("-import-error")
        stage.border_title = f"Cannot play: {self.effect_name} (Esc to edit)"
        self.query_one("#import-error-text", Static).update(self._broken[self.effect_name])
        if self.focused in (self.editor, self.query_one("#canvas")):
            self.query_one("#effects").focus()
        self.state = "finished"
        self._frame_index = 0
        self._update_transport()

    def _failure_location(self, error: BaseException) -> str:
        """Return where in a development effect's file `error` was raised, as ` at file:line`, or nothing."""
        location = None if self._development is None else self._development.location(error)
        return f" at {location}" if location else ""

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
            elif scope in self._broken:
                return []
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
        options_panel = self.query_one("#options")
        options_panel.border_title = f"Options · {effect_name}"
        options_panel.border_subtitle = self._description(effect_name)
        grid = self.query_one("#effect-options")
        # Editors show each option's last valid value, so errors from an earlier visit no longer apply.
        self._errors.pop(effect_name, None)
        await grid.remove_children()
        await grid.mount_all(self._editors(effect_name))
        self._refresh_subtitle()

    @on(OptionEditor.Edited)
    def _option_edited(self, event: OptionEditor.Edited) -> None:
        editor = event.editor
        errors = self._errors.setdefault(editor.scope, {})
        if editor.error is None:
            errors.pop(editor.option.name, None)
            values = self._values.setdefault(editor.scope, {})
            previous = values.get(editor.option.name, editor.option.default)
            if editor.value == editor.option.default:
                values.pop(editor.option.name, None)
            else:
                values[editor.option.name] = editor.value
            if editor.scope == _TERMINAL_SCOPE and editor.option.name == "tab_width":
                self.editor.indent_width = editor.value
            if editor.value != previous:
                self._schedule_auto_replay()
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

    def _open_file(self, path: Path) -> bool:
        """Load the text of the file at `path` into the editor. Return whether it could be read."""
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            self.notify(f"Cannot open {path}: {error}", severity="error")
            return False
        self.action_stop()
        self.input_file = str(path)
        self._load_text(text)
        self._file_text = self.editor.text
        return True

    def action_open(self) -> None:
        """Ask for a file and load its text into the editor."""

        def load(result: tuple[str, bool] | None) -> None:
            if result is not None:
                path = Path(result[0]).expanduser()
                if self._open_file(path):
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

    # Commands --------------------------------------------------------------------------------------------------

    def action_command(self) -> None:
        """Show the CLI command for the selected effect and current options, and load a pasted command."""
        command = ""
        if not self._current_errors():
            command = options.command_line(
                self.effect_name,
                self._scope_values(self.effect_name),
                self._scope_values(_TERMINAL_SCOPE),
                # A file edited since it was opened or saved no longer holds the previewed text.
                self.input_file if self.editor.text == self._file_text else None,
            )

        async def load(pasted: str | None) -> None:
            if pasted:
                await self.apply_command(pasted)

        self.push_screen(CommandScreen(command), load)

    async def apply_command(self, command: str) -> None:
        """Set the effect and options from a `tte` command line.

        Options the command leaves out take their CLI defaults, so the TUI plays what the command would play.
        """
        effect_fields = {name: functools.partial(self._scope_fields, name) for name in self.effect_resource_map}
        try:
            parsed = options.parse_command(command, effect_fields, self._scope_fields(_TERMINAL_SCOPE))
        except ValueError as error:
            self.notify(f"Cannot load the command: {error}", severity="error")
            return
        self.action_stop()
        effect_values = {}
        for option in self._scope_fields(parsed.effect):
            value = parsed.effect_values.get(option.name, option.default)
            if value != option.default:
                effect_values[option.name] = value
        terminal_values = {}
        for option in self._scope_fields(_TERMINAL_SCOPE):
            value = parsed.terminal_values.get(option.name, option.spec.normalize(option.spec.default))
            if value != option.default:
                terminal_values[option.name] = value
        self._values[parsed.effect] = effect_values
        self._values[_TERMINAL_SCOPE] = terminal_values
        self._errors.pop(_TERMINAL_SCOPE, None)
        for editor in self.query(OptionEditor):
            if editor.scope == _TERMINAL_SCOPE:
                editor.set_value(self._value(_TERMINAL_SCOPE, editor.option))
        self.editor.indent_width = self._tab_width()
        await self._show_effect(parsed.effect)
        self._highlight_effect(parsed.effect)
        problems = list(parsed.problems)
        if parsed.input_file:
            problem = self._open_command_file(parsed.input_file)
            if problem:
                problems.append(problem)
        message = f"Loaded {parsed.effect} from the command."
        if problems:
            self.notify(message + "\nSkipped: " + "; ".join(problems), severity="warning", timeout=10)
        else:
            self.notify(message)

    def _open_command_file(self, input_file: str) -> str | None:
        """Load the text of a command's input file. Return why it was not loaded, or `None`."""
        path = Path(input_file).expanduser()
        if not path.is_file():
            return f"input file {path} was not found, so the text is unchanged"
        if not self._open_file(path):
            return f"input file {path} could not be read"
        return None

    def action_help(self) -> None:
        """Show the keys and tips."""
        self.push_screen(HelpScreen())

    # Canvas ----------------------------------------------------------------------------------------------------

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
        lines = self.editor.document.lines
        if len(lines) > area.height or max(map(cell_len, lines), default=0) > area.width:
            subtitle += " · more text, scroll to see"
        errors = self._current_errors()
        if errors:
            subtitle = f"[{len(errors)} invalid option{'s' if len(errors) != 1 else ''}] " + subtitle
        self._canvas_note = subtitle
        self._update_status()

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

    def text_size(self) -> tuple[int, int]:
        """Return the width and height of the text as the engine lays it out in the effect area."""
        area_width, area_height = self._canvas_size()
        values = {option.name: value for option, value in self._scope_values(_TERMINAL_SCOPE)}
        values.update(canvas_width=-1, canvas_height=-1)
        config = typing.cast("TerminalConfig", options.build_config(TerminalConfig, values))
        terminal = Terminal(self.editor.colored_text(), config, terminal_dimensions=(area_width, area_height))
        return terminal.canvas.width, terminal.canvas.height

    def action_fit_canvas(self) -> None:
        """Set the canvas size to the size of the text."""
        if self._errors.get(_TERMINAL_SCOPE):
            self.notify("Fix the invalid canvas options first.", severity="error")
            return
        if not self.editor.text.strip():
            self.notify("Type or open some text to fit the canvas to.", severity="warning")
            return
        try:
            width, height = self.text_size()
        except Exception as error:  # noqa: BLE001
            self.notify(f"Cannot measure the text: {error}", severity="error")
            return
        self.post_message(ColorTextArea.CanvasResized(width, height))

    def action_maximize_canvas(self) -> None:
        """Grow the canvas to the whole effect area."""
        area_width, area_height = self._canvas_size()
        self.post_message(ColorTextArea.CanvasResized(area_width, area_height))

    @on(CanvasView.Clicked)
    def _canvas_clicked(self, message: CanvasView.Clicked) -> None:
        """Stop the effect and put the cursor where the text area was clicked."""
        self.action_stop()
        editor = self.editor
        editor.focus()
        editor.cursor_location = editor.get_target_document_location(message.event)

    def copy_to_clipboard(self, text: str) -> None:
        """Copy `text` with OSC 52 for the terminal, and with the system clipboard command where there is one.

        Many terminals, including macOS Terminal and iTerm2 by default, ignore OSC 52.
        """
        super().copy_to_clipboard(text)
        self.copied_to_system_clipboard = clipboard.copy_with_system_command(text)

    # Text toolbar ----------------------------------------------------------------------------------------------

    def _back_to_text(self) -> ColorTextArea:
        """Stop any effect and focus the editor, keeping its cursor and selection."""
        self.action_stop()
        self.editor.focus()
        return self.editor

    @on(menu.ContextRequested)
    def _context_menu(self, message: menu.ContextRequested) -> None:
        """Offer editing, color, symbol, canvas, and playback actions where the mouse was right-clicked."""
        if self.screen.is_modal:
            return
        has_selection = bool(self.editor.selected_text)
        shown = self.state != "editing"
        items: list[menu.MenuItem | None] = [
            menu.MenuItem("Cut", "cut", "Ctrl+X", has_selection),
            menu.MenuItem("Copy", "copy", "Ctrl+C", has_selection),
            menu.MenuItem("Paste", "paste", "Ctrl+V"),
            menu.MenuItem("Select all", "select_all"),
            None,
            menu.MenuItem("Text color…", "fg"),
            menu.MenuItem("Background color…", "bg"),
            menu.MenuItem("Clear colors", "clear"),
            menu.MenuItem("Insert symbol…", "symbols"),
            None,
            menu.MenuItem("Pause" if self.state == "playing" else "Play", "play", "F5"),
            menu.MenuItem("Stop", "stop", "Esc", shown),
            menu.MenuItem("Fit canvas to text", "fit", "Ctrl+T"),
            menu.MenuItem("Maximize canvas", "max", "Ctrl+G"),
        ]

        def chosen(action: str | None) -> None:
            if action is not None:
                self._run_menu_action(action, message.at)

        self.push_screen(menu.ContextMenu(items, message.at), chosen)

    def _run_menu_action(self, action: str, at: Offset) -> None:
        playback = {"play": self.action_play, "stop": self.action_stop}
        canvas_actions = {"fit": self.action_fit_canvas, "max": self.action_maximize_canvas}
        if action in playback:
            playback[action]()
            return
        if action in canvas_actions:
            canvas_actions[action]()
            return
        editor = self._back_to_text()
        if action in ("cut", "copy", "paste"):
            with contextlib.suppress(SkipAction):
                getattr(editor, f"action_{action}")()
        elif action == "select_all":
            editor.select_all()
        elif action in ("fg", "bg"):
            self._pick_text_color(TextToolbar.PickColor(typing.cast("Layer", action)))
        elif action == "clear":
            self._clear_text_color()
        elif action == "symbols":
            self._open_symbols(TextToolbar.OpenSymbols(at))

    @on(TextToolbar.OpenSymbols)
    def _open_symbols(self, message: TextToolbar.OpenSymbols) -> None:
        editor = self._back_to_text()

        def closed(_result: None) -> None:
            editor.focus()

        self.push_screen(SymbolScreen(editor.insert_symbol, message.at), closed)

    @on(TextToolbar.PickColor)
    def _pick_text_color(self, message: TextToolbar.PickColor) -> None:
        editor = self._back_to_text()
        layer = message.layer
        pen = editor.pen or colors.CellStyle()
        current = pen.fg if layer == "fg" else pen.bg
        title = "text" if layer == "fg" else "text background"

        def recolor(style: colors.CellStyle | None, color: Color | None) -> colors.CellStyle | None:
            updated = dataclasses.replace(style or colors.CellStyle(), **{layer: color})
            return None if updated == colors.CellStyle() else updated

        def apply(result: tuple[Color, ...] | None) -> None:
            editor.focus()
            if result is None:
                return
            # An empty result is No color.
            color = result[0] if result else None
            editor.pen = dataclasses.replace(editor.pen or colors.CellStyle(), **{layer: color})
            if editor.paint_selection(lambda style: recolor(style, color)):
                # Deselect so the new colors show instead of the selection highlight.
                editor.move_cursor(editor.selection.end)
            self._show_pen()
            self._suggest_color_handling()

        self.push_screen(ColorScreen(title, [current or Color("ffffff")], multiple=False, allow_none=True), apply)

    @on(GradientChip.Apply)
    def _apply_gradient(self) -> None:
        """Color the selection with the gradient, or open the gradient dialog when nothing is selected."""
        editor = self._back_to_text()
        if editor.selection.is_empty:
            self._edit_gradient()
            return
        editor.paint_gradient(self._gradient)
        # Deselect so the new colors show instead of the selection highlight.
        editor.move_cursor(editor.selection.end)
        self._suggest_color_handling()

    @on(GradientChip.Edit)
    def _edit_gradient(self) -> None:
        """Open the gradient dialog, and apply the new gradient to the selection when there is one."""
        editor = self._back_to_text()

        def built(result: TextGradient | None) -> None:
            editor.focus()
            if result is None:
                return
            self._gradient = result
            self.query_one(GradientChip).show(result)
            if editor.paint_gradient(result):
                editor.move_cursor(editor.selection.end)
                self._suggest_color_handling()

        self.push_screen(GradientScreen(self._gradient, has_selection=not editor.selection.is_empty), built)

    @on(TextToolbar.ClearColor)
    def _clear_text_color(self) -> None:
        editor = self._back_to_text()
        # Type plain text from here on, rather than extending the color of the character before the cursor.
        editor.pen = colors.CellStyle()
        editor.paint_selection(lambda _style: None)
        self._show_pen()

    def _show_pen(self) -> None:
        pen = self.editor.pen
        self.query_one(TextToolbar).show_colors(pen.fg if pen else None, pen.bg if pen else None)

    def _suggest_color_handling(self) -> None:
        """Point out once that effects ignore text colors until existing color handling is changed."""
        if self._color_hint_shown or self._value_of("existing_color_handling") != "ignore":
            return
        self._color_hint_shown = True
        self.notify(
            "Effects ignore text colors until existing color handling on the Canvas tab is 'always' or 'dynamic'.",
            timeout=8,
        )

    def action_toggle_panel(self, handle_id: str) -> None:
        """Show or hide the panel of the drawer handle `handle_id`."""
        self.query_one(f"#{handle_id}", DrawerHandle).toggle()

    @on(DrawerHandle.Toggled)
    def _panel_toggled(self, event: DrawerHandle.Toggled) -> None:
        """Show or hide the effect list or the options panel, giving its room to the text area."""
        event.stop()
        handle = event.handle
        panel = self.query_one("#effects-panel" if handle.id == "effects-drawer" else "#options")
        if not handle.open and panel.has_focus_within:
            self.editor.focus()
        panel.display = handle.open
        self.call_after_refresh(self._refresh_subtitle)

    def on_resize(self, event: Resize) -> None:
        """Fit the option columns to the screen width and update the canvas size shown under the text area."""
        columns = max(1, min(3, event.size.width // _OPTION_COLUMN_WIDTH))
        for grid in self.query(".option-grid"):
            grid.styles.grid_size_columns = columns
        self.call_after_refresh(self._refresh_subtitle)

    # Playback --------------------------------------------------------------------------------------------------

    def build_effect(self) -> BaseEffect | None:
        """Return the selected effect configured with the current options and text, or `None` if it cannot run."""
        if self.effect_name in self._broken:
            self.notify(f"{self.effect_name} cannot be played.", severity="error")
            return None
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
            self.notify(
                f"Cannot create {self.effect_name}{self._failure_location(error)}: {error}",
                severity="error",
            )
            return None
        effect._terminal_dimensions_override = self._canvas_size()
        return effect

    def _settings_key(self) -> tuple[typing.Any, ...]:
        """Return a value that changes whenever the effect would play differently, apart from its randomness."""
        return (
            self.effect_name,
            self._reloads,
            repr(sorted(self._values.get(self.effect_name, {}).items())),
            repr(sorted(self._values.get(_TERMINAL_SCOPE, {}).items())),
            self.editor.colored_text(),
            self._canvas_size(),
        )

    def start_playback(self, *, focus: bool = True, reuse: bool = False) -> bool:
        """Play the selected effect from the start. Return whether it started.

        Frames are produced on a background thread, so building the effect does not freeze the interface. With
        `reuse`, the frames of the last complete run are replayed when the settings have not changed since, as a
        loop does. With `focus`, the canvas takes focus so Space and the arrow keys control playback.
        """
        if self.effect_name in self._broken:
            self._show_import_error()
            return False
        if self.query_one("#stage").has_class("-import-error"):
            self.action_stop()
        self._cancel_playback()
        effect = self.build_effect()
        if effect is None:
            return False
        key = self._settings_key()
        stream: frames.FrameStream | frames.RecordedFrames
        if reuse and self._recorded is not None and self._recorded[0] == key:
            stream = frames.RecordedFrames(self._recorded[1])
            self._recording = None
        else:
            stream = frames.FrameStream(effect)
            self._recording = []
        self._playback_key = key
        stream.start()
        self._stream = stream
        canvas_view = self.query_one("#canvas", CanvasView)
        canvas_view.clear()
        stage = self.query_one("#stage")
        stage.remove_class("-import-error")
        stage.add_class("-playing")
        stage.border_title = f"Preparing: {self.effect_name}"
        if focus or self.focused is self.editor:
            canvas_view.focus()
        self.state = "playing"
        self._frame_index = 0
        self._history.clear()
        self._back = 0
        self._shown_at.clear()
        self._frame_rate = effect.terminal_config.frame_rate or _MAX_UNLIMITED_FPS
        self._run_frames()
        self._update_transport()
        return True

    def _run_frames(self) -> None:
        """Start the frame timer, polling slowly until the first frame is ready.

        Once frames arrive, the timer ticks twice per frame and shows a frame whenever one is due, so a tick that
        runs late delays one frame instead of skipping it and lowering the frame rate.
        """
        if self._timer is not None:
            self._timer.stop()
        interval = 1 / self._frame_rate
        self._due = time.monotonic()
        tick = _PREPARE_POLL if self._frame_index == 0 else max(interval / 2, _MIN_TICK)
        self._timer = self.query_one("#canvas").set_interval(tick, self._tick)

    def _tick(self) -> None:
        """Show the next frame if it is due."""
        now = time.monotonic()
        if now < self._due:
            return
        interval = 1 / self._frame_rate
        # Catch up on a late frame by at most one interval, rather than rushing through several.
        self._due = max(self._due + interval, now - interval)
        self._next_frame()

    def _next_frame(self) -> None:
        """Show the next frame when it is ready, or finish when the effect is complete.

        After stepping back, the frames already shown are shown again before the effect continues.
        """
        if self._back:
            self._back -= 1
            self._show_history()
            self._shown_at.append(time.monotonic())
            return
        stream = self._stream
        if stream is None:
            return
        frame = stream.poll()
        if frame is not None:
            self._show(frame)
        elif stream.finished:
            if stream.error is not None:
                self._finish("Failed")
                self.notify(
                    f"{self.effect_name} failed{self._failure_location(stream.error)}: {stream.error}",
                    severity="error",
                )
            else:
                self._finish("Finished")

    def _show(self, frame: frames.Frame) -> None:
        """Display `frame` and count it for the frame rate."""
        if self._recording is not None:
            if len(self._recording) < _MAX_KEPT_FRAMES:
                self._recording.append(frame)
            else:
                self._recording = None
        self.query_one("#canvas", CanvasView).show_strips(frame)
        self._history.append(frame)
        self._frame_index += 1
        self._shown_at.append(time.monotonic())
        if self._frame_index == 1:
            # The effect's objects live until playback ends. Freezing them keeps full garbage collections, which
            # scan every object and can stall a frame for a tenth of a second, from rescanning them.
            gc.freeze()
            self.query_one("#stage").border_title = f"Playing: {self.effect_name}"
            if self.state == "playing":
                self._run_frames()

    def _finish(self, label: str) -> None:
        """Stop advancing frames and keep the last frame on screen. With Loop on, replay after a pause."""
        stream = self._stream
        if isinstance(stream, frames.FrameStream) and stream.error is None and self._recording is not None:
            self._recorded = (typing.cast("tuple[typing.Any, ...]", self._playback_key), self._recording)
        self._recording = None
        self._stop_frames()
        self.state = "finished"
        self.query_one("#stage").border_title = f"{label}: {self.effect_name} (Esc to edit)"
        if label == "Finished" and self.query_one("#loop", Checkbox).value:
            self._loop_timer = self.query_one("#stage").set_timer(_LOOP_PAUSE, self._loop_again)
        self._update_transport()

    def _loop_again(self) -> None:
        """Replay a finished effect while Loop is on."""
        self._loop_timer = None
        if self.state == "finished" and self.query_one("#loop", Checkbox).value and not self.screen.is_modal:
            self.start_playback(focus=False, reuse=True)

    def _stop_frames(self) -> None:
        """Stop the frame timer and the frame stream, and let the garbage collector see the effect again."""
        gc.unfreeze()
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        if self._stream is not None:
            self._stream.close()
            self._stream = None

    def _cancel_playback(self) -> None:
        """Stop the frames, and cancel a pending loop or auto-replay."""
        self._stop_frames()
        for timer in (self._loop_timer, self._auto_timer):
            if timer is not None:
                timer.stop()
        self._loop_timer = self._auto_timer = None

    def action_play(self) -> None:
        """Play the effect, pause or resume it, or replay it once finished."""
        if self.state == "playing":
            self._pause()
        elif self.state == "paused":
            self._resume()
        else:
            self.start_playback()

    def action_replay(self) -> None:
        """Play the effect from the start."""
        self.start_playback()

    def _pause(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        self.state = "paused"
        self.query_one("#stage").border_title = f"Paused: {self.effect_name} (Space to resume, ← → to step)"
        self._update_transport()

    def _resume(self) -> None:
        self.state = "playing"
        self.query_one("#stage").border_title = f"Playing: {self.effect_name}"
        self._shown_at.clear()
        self._run_frames()
        self._update_transport()

    def action_step(self) -> None:
        """Pause, then show one more frame. Once the effect has finished, step forward to its last frame."""
        if self.state == "playing":
            self._pause()
        if self.state == "finished" and self._back:
            self._back -= 1
            self._show_history()
        elif self.state == "paused":
            self._next_frame()
        self._update_transport()

    def action_step_back(self) -> None:
        """Pause, then show the frame before the one on screen, while earlier frames are kept."""
        if self.state == "playing":
            self._pause()
        if self.state not in ("paused", "finished") or self._back + 1 >= len(self._history):
            return
        if self._loop_timer is not None:
            # Loop would replay from the start while the frames are being looked through.
            self._loop_timer.stop()
            self._loop_timer = None
        self._back += 1
        self._show_history()
        self._update_transport()

    def _show_history(self) -> None:
        """Display the kept frame `_back` frames before the newest one."""
        self.query_one("#canvas", CanvasView).show_strips(self._history[-1 - self._back])

    def action_stop(self) -> None:
        """Stop the effect and return to the text."""
        if self.state == "editing":
            return
        self._cancel_playback()
        self._recording = None
        self._history.clear()
        self._back = 0
        self.state = "editing"
        stage = self.query_one("#stage")
        stage.remove_class("-playing", "-import-error")
        stage.border_title = "Text"
        canvas_view = self.query_one("#canvas", CanvasView)
        if self.focused is canvas_view:
            self.editor.focus()
        canvas_view.clear()
        self._update_transport()

    def _schedule_auto_replay(self) -> None:
        """Replay the effect shortly after the last change, while Auto-replay is on."""
        if not self.query_one("#auto-replay", Checkbox).value:
            return
        if self._auto_timer is not None:
            self._auto_timer.stop()
        self._auto_timer = self.query_one("#stage").set_timer(_AUTO_REPLAY_DELAY, self._auto_replay)

    def _auto_replay(self) -> None:
        self._auto_timer = None
        if not self.query_one("#auto-replay", Checkbox).value or self.screen.is_modal or self._current_errors():
            return
        if self.editor._drag_edges:
            # Replaying would hide the text area mid-drag, so wait for the drag to end.
            self._schedule_auto_replay()
            return
        self.start_playback(focus=False)

    @on(Checkbox.Changed, "#loop")
    def _loop_changed(self, event: Checkbox.Changed) -> None:
        if event.value and self.state == "finished":
            self._loop_timer = self.query_one("#stage").set_timer(_LOOP_PAUSE, self._loop_again)

    @on(Button.Pressed)
    async def _transport_pressed(self, event: Button.Pressed) -> None:
        if event.button.parent is None or event.button.parent.id != "transport":
            return
        action = event.button.id
        if action == "random":
            await self.action_random()
        elif action == "stop":
            self.action_stop()
        elif action == "fit":
            self.action_fit_canvas()
        elif action == "max":
            self.action_maximize_canvas()
        elif action in ("play", "step", "step_back", "open", "save", "export"):
            getattr(self, f"action_{action}")()

    def _update_transport(self) -> None:
        """Label the play button for the playback state, and enable the buttons that apply."""
        self.query_one("#play", Button).label = "❚❚ Pause" if self.state == "playing" else "▶ Play"
        self.query_one("#stop", Button).disabled = self.state == "editing"
        self.query_one("#step", Button).disabled = not self._can_step()
        self.query_one("#step_back", Button).disabled = not self._can_step_back()
        self.refresh_bindings()
        self._update_status()

    def measured_fps(self) -> float:
        """Return the frames shown per second over the last second of playback."""
        if self.state != "playing" or len(self._shown_at) < 2:
            return 0.0
        now = time.monotonic()
        recent = [shown for shown in self._shown_at if now - shown <= 1.0]
        if len(recent) < 2 or now - recent[-1] > 1.0:
            return 0.0
        return (len(recent) - 1) / max(recent[-1] - recent[0], 1e-6)

    def _update_status(self) -> None:
        """Show the canvas size under the text area, with the frame count and frame rate while an effect is shown."""
        if self.state == "editing":
            text = f"{self._canvas_note} · drag the outline to resize"
        else:
            text = f"frame {self._frame_index - self._back}"
            if self._back:
                text += f" of {self._frame_index}"
            if self.state == "playing":
                target = self._value_of("frame_rate")
                text += f" · {self.measured_fps():.0f} fps"
                if target:
                    text += f" of {target}"
            text += f" · {self._canvas_note}"
        stage = self.query_one("#stage")
        if stage.border_subtitle != text:
            stage.border_subtitle = text

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:  # noqa: ARG002
        """Offer Stop and the step actions only while they apply, and only Quit while a dialog is open."""
        if self.screen.is_modal:
            return action == "quit"
        if action == "stop":
            return self.state != "editing"
        if action == "step":
            return self._can_step()
        if action == "step_back":
            return self._can_step_back()
        return True

    def _can_step(self) -> bool:
        """Return whether a later frame can be shown: while playing or paused, or after stepping back."""
        return self.state in ("playing", "paused") or (self.state == "finished" and self._back > 0)

    def _can_step_back(self) -> bool:
        """Return whether an earlier frame can be shown: while playing, or when one is kept."""
        return self.state == "playing" or (self.state != "editing" and self._back + 1 < len(self._history))

    # Export ----------------------------------------------------------------------------------------------------

    def action_export(self) -> None:
        """Ask for a file and a format, and export the selected effect to it."""
        if self._value_of("frame_rate") == 0:
            self.notify("Exporting needs a frame rate greater than 0 (Canvas tab).", severity="error")
            return
        if self.query_one(ExportProgress).display:
            self.notify("An export is already running.", severity="warning")
            return

        def export_to(result: tuple[str, bool] | None) -> None:
            if result is None:
                return
            effect = self.build_effect()
            if effect is not None:
                # Export only the canvas, as the command line records it, rather than the whole text area around it.
                rect = self._canvas_geometry()
                effect._terminal_dimensions_override = (rect.width, rect.height)
                self.query_one(ExportProgress).start(self.effect_name)
                self._export(effect, self.effect_name, Path(result[0]).expanduser())

        file_formats = [FileFormat(fmt.name, fmt.suffix, export.format_problem(fmt)) for fmt in export.FORMATS]
        self.push_screen(
            FileScreen(
                "Export effect",
                f"{self.effect_name}{self._export_suffix}",
                mode="save",
                formats=file_formats,
            ),
            export_to,
        )

    @work(thread=True, exclusive=True, group="export")
    def _export(self, effect: BaseEffect, effect_name: str, path: Path) -> None:
        """Render the effect to a recording without displaying it, then convert it for GIF or WebP."""
        from terminaltexteffects.__main__ import _record_playbacks  # noqa: PLC0415
        from terminaltexteffects.engine._recording import RecordingError  # noqa: PLC0415

        progress = self.query_one(ExportProgress)
        fmt = export.format_for(path)
        self._export_suffix = fmt.suffix
        last_update = 0.0

        def on_frame(count: int) -> None:
            nonlocal last_update
            now = time.monotonic()
            if now - last_update >= _STATUS_INTERVAL:
                last_update = now
                self.call_from_thread(progress.show_frames, count)

        def on_step(frame_count: int, step: str, count: int, total: int | None) -> None:
            nonlocal last_update
            now = time.monotonic()
            if now - last_update >= _STATUS_INTERVAL or count == total:
                last_update = now
                self.call_from_thread(progress.show_step, step, count, total or frame_count)

        missing: frozenset[str] = frozenset()
        try:
            if fmt is export.FORMATS[0]:
                header, frame_count, _ = _record_playbacks(path, effect_name, effect, 1, on_frame=on_frame)
            else:
                with tempfile.TemporaryDirectory(prefix="tte-export-") as folder:
                    recording = Path(folder) / f"effect{export.FORMATS[0].suffix}"
                    header, frame_count, _ = _record_playbacks(recording, effect_name, effect, 1, on_frame=on_frame)
                    self.call_from_thread(progress.show_rendering, fmt.name, frame_count)
                    missing = export.export_recording(
                        recording,
                        path,
                        fmt,
                        fps=header.frame_rate,
                        on_progress=functools.partial(on_step, frame_count),
                    )
        except (OSError, RecordingError, ValueError, export.ExportError) as error:
            self.call_from_thread(progress.finish)
            self.call_from_thread(self.notify, f"Export failed: {error}", severity="error")
            return
        except Exception as error:  # noqa: BLE001 (an effect can raise anything, and the export must still end)
            self.call_from_thread(progress.finish)
            self.call_from_thread(self.notify, f"Export failed: {type(error).__name__}: {error}", severity="error")
            return
        summary = (
            f"Exported {frame_count} frames ({header.width}x{header.height} at {header.frame_rate} fps) to {path}."
        )
        if fmt is export.FORMATS[0]:
            summary += f" Play it with: tte --play {path}"
        if missing:
            summary += f" No installed font has these symbols, drawn as boxes: {' '.join(sorted(missing))}"
        self.call_from_thread(progress.finish)
        self.call_from_thread(self.notify, summary)
