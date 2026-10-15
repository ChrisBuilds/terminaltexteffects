"""Tests for the TUI canvas outline geometry and dragging."""

from __future__ import annotations

import asyncio
import typing
from typing import TYPE_CHECKING

import pytest
from rich.style import Style
from textual.widgets import Input

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.tui import canvas
from terminaltexteffects.tui.app import TTEApp

if TYPE_CHECKING:
    from textual.pilot import Pilot

_, _EFFECTS = build_parser(include_user_effects=False)


@pytest.mark.parametrize(
    ("anchor", "expected"),
    [
        ("nw", canvas.CanvasRect(0, 0, 40, 10)),
        ("se", canvas.CanvasRect(60, 20, 40, 10)),
        ("c", canvas.CanvasRect(30, 10, 40, 10)),
        ("s", canvas.CanvasRect(30, 20, 40, 10)),
        ("e", canvas.CanvasRect(60, 10, 40, 10)),
    ],
)
def test_canvas_rect_follows_the_anchor(anchor: str, expected: canvas.CanvasRect) -> None:
    """The canvas should sit where the engine places it for each anchor."""
    assert canvas.canvas_rect(100, 30, 40, 10, anchor) == expected


def test_canvas_rect_matches_the_engine_for_odd_sizes() -> None:
    """Centered canvases should round like the engine, which counts rows from the bottom."""
    from terminaltexteffects.engine.terminal import Terminal, TerminalConfig  # noqa: PLC0415

    config = TerminalConfig._build_config()
    config.canvas_width, config.canvas_height, config.anchor_canvas = 7, 4, "c"
    terminal = Terminal("x", config, terminal_dimensions=(20, 11))
    rect = canvas.canvas_rect(20, 11, 7, 4, "c")
    assert rect.left == terminal.canvas_column_offset
    assert 11 - rect.bottom == terminal.canvas_row_offset


def test_draggable_edges_move_away_from_the_anchor() -> None:
    """Only edges that move when the canvas is resized should be draggable."""
    assert canvas.draggable_edges("nw") == {"right", "bottom"}
    assert canvas.draggable_edges("se") == {"left", "top"}
    assert canvas.draggable_edges("c") == {"left", "right", "top", "bottom"}


@pytest.mark.parametrize("anchor", ["nw", "c", "se", "n", "w"])
def test_dragged_size_puts_the_edge_under_the_pointer(anchor: str) -> None:
    """Dragging an edge to the outline position of a canvas size should give back that size."""
    for width in (10, 41, 60):
        rect = canvas.canvas_rect(100, 30, width, 10, anchor)
        for edge in canvas.draggable_edges(anchor) & {"left", "right"}:
            position = rect.right if edge == "right" else rect.left - 1
            assert abs(canvas.dragged_size(edge, position, 100, anchor) - width) <= 1


def test_dragged_size_is_clamped() -> None:
    """Dragged sizes should stay between one cell and the whole area."""
    assert canvas.dragged_size("right", -5, 100, "nw") == 1
    assert canvas.dragged_size("right", 500, 100, "nw") == 100


def test_edges_at_finds_edges_and_corners() -> None:
    """The outline cells just outside the canvas should hit their edges, and corners should hit both."""
    rect = canvas.CanvasRect(0, 0, 40, 10)
    edges = canvas.draggable_edges("nw")
    assert canvas.edges_at(rect, 40, 5, edges) == {"right"}
    assert canvas.edges_at(rect, 20, 10, edges) == {"bottom"}
    assert canvas.edges_at(rect, 40, 10, edges) == {"right", "bottom"}
    assert canvas.edges_at(rect, 20, 5, edges) == set()


def _run(app: TTEApp, script: typing.Callable[[TTEApp, Pilot[None]], typing.Awaitable[None]]) -> None:
    async def main() -> None:
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await script(app, pilot)

    asyncio.run(main())


async def _set_canvas(app: TTEApp, pilot: Pilot[None], width: str, height: str) -> None:
    app.query_one("#option-terminal-canvas_width").query_one(Input).value = width
    app.query_one("#option-terminal-canvas_height").query_one(Input).value = height
    await pilot.pause()


def test_canvas_area_leaves_room_for_the_outline() -> None:
    """The effect area should give up one cell beyond each movable edge."""
    assert canvas.canvas_area(100, 30, "nw") == canvas.CanvasRect(0, 0, 99, 29)
    assert canvas.canvas_area(100, 30, "c") == canvas.CanvasRect(1, 1, 98, 28)
    assert canvas.canvas_area(100, 30, "se") == canvas.CanvasRect(1, 1, 99, 29)


def test_outline_is_always_visible() -> None:
    """The outline should be drawn in full blocks just outside the canvas, also when the canvas fills the area."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        width, height = app._canvas_size()
        stage = app.query_one("#stage").content_size
        assert (width, height) == (stage.width - 1, stage.height - 1)
        assert app.editor.canvas_rect == canvas.CanvasRect(0, 0, width, height)
        bottom = app.editor.render_line(height).text
        assert bottom.replace(" CANVAS ", "█" * len(" CANVAS ")) == "█" * (width + 1)
        assert bottom.index(" CANVAS ") == (width - len(" CANVAS ")) // 2
        assert app.editor.render_line(0).text.endswith("█")
        await _set_canvas(app, pilot, "30", "5")
        assert app.editor.canvas_rect == canvas.CanvasRect(0, 0, 30, 5)
        assert "canvas 30x5" in str(app.query_one("#stage").border_subtitle)
        assert app.editor.render_line(5).text.startswith("█" * 11 + " CANVAS " + "█" * 12)
        effect = app.build_effect()
        assert effect is not None
        assert effect._terminal_dimensions_override == (width, height)

    _run(TTEApp(_EFFECTS, "Hello", effect="wipe"), script)


def test_outline_follows_the_text_for_text_sized_canvases() -> None:
    """A canvas dimension of -1 should be measured from the text, as the engine does."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await _set_canvas(app, pilot, "-1", "-1")
        assert app.editor.canvas_rect == canvas.CanvasRect(0, 0, 5, 2)

    _run(TTEApp(_EFFECTS, "Hello\nthere", effect="wipe"), script)


def test_dragging_the_outline_resizes_the_canvas() -> None:
    """Dragging the outline corner should set both canvas options without selecting text."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await _set_canvas(app, pilot, "30", "5")
        await pilot.mouse_down("#editor", offset=(30, 5))
        await pilot.hover("#editor", offset=(50, 8))
        await pilot.mouse_up("#editor", offset=(50, 8))
        await pilot.pause()
        assert (app._value_of("canvas_width"), app._value_of("canvas_height")) == (50, 8)
        assert app.editor.selection.is_empty

    _run(TTEApp(_EFFECTS, "Hello", effect="wipe"), script)


def test_dragging_a_full_canvas_edge_shrinks_and_restores_it() -> None:
    """The outline of a full canvas should be draggable, and dragging back to the end of the area stores 0."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        width, _ = app._canvas_size()
        await pilot.mouse_down("#editor", offset=(width, 4))
        await pilot.hover("#editor", offset=(40, 4))
        await pilot.mouse_up("#editor", offset=(40, 4))
        await pilot.pause()
        assert (app._value_of("canvas_width"), app._value_of("canvas_height")) == (40, 0)
        await pilot.mouse_down("#editor", offset=(40, 4))
        await pilot.hover("#editor", offset=(width, 4))
        await pilot.mouse_up("#editor", offset=(width, 4))
        await pilot.pause()
        assert app._value_of("canvas_width") == 0

    _run(TTEApp(_EFFECTS, "Hello", effect="wipe"), script)


def test_outline_edges_light_up_under_the_mouse() -> None:
    """Hovering an edge should light it, a corner should light both of its edges, and leaving should clear them."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await _set_canvas(app, pilot, "30", "5")
        editor = app.editor
        await pilot.hover("#editor", offset=(30, 2))
        assert editor._hover_edges == {"right"}
        await pilot.hover("#editor", offset=(30, 5))
        assert editor._hover_edges == {"right", "bottom"}
        hot = Style(color=app.theme_variables["foreground"])
        corner = editor.render_line(5).divide([30, 31])[1]
        assert all(segment.style is not None and segment.style.color == hot.color for segment in corner)
        await pilot.hover("#editor", offset=(5, 2))
        assert editor._hover_edges == set()

    _run(TTEApp(_EFFECTS, "Hello", effect="wipe"), script)
