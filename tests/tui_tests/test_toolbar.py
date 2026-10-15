"""Pilot tests for the text toolbar: text colors and symbol palettes."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.widgets import Input, Select
from textual.widgets.text_area import Selection

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.tui import colors
from terminaltexteffects.tui.app import TTEApp
from terminaltexteffects.tui.gradient import GradientScreen, TextGradient
from terminaltexteffects.tui.picker import ColorScreen
from terminaltexteffects.tui.toolbar import SYMBOL_GROUPS, SymbolGrid, SymbolScreen, TextToolbar
from terminaltexteffects.utils.graphics import Color, Gradient

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from textual.pilot import Pilot

_, _EFFECTS = build_parser(include_user_effects=False)


def _run(app: TTEApp, script: Callable[[TTEApp, Pilot[None]], Awaitable[None]]) -> None:
    async def main() -> None:
        async with app.run_test(size=(120, 34)) as pilot:
            await pilot.pause()
            await script(app, pilot)
            app._cancel_playback()

    asyncio.run(main())


def test_symbol_palette_inserts_at_the_cursor_and_replaces_the_selection() -> None:
    """The palette should insert each chosen symbol at the cursor, replacing selected text, until it is closed."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.editor
        editor.focus()
        editor.selection = Selection((0, 0), (0, 2))
        await pilot.click("#symbols")
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, SymbolScreen)
        grid = screen.query_one(SymbolGrid)
        assert app.focused is grid
        await pilot.press("enter")
        assert editor.text == f"{SYMBOL_GROUPS['Blocks'][0]}cd"
        await pilot.press("down", "right", "enter")
        assert editor.text == f"{SYMBOL_GROUPS['Blocks'][0]}{SYMBOL_GROUPS['Lines'][1]}cd"
        assert editor.cursor_location == (0, 2)
        await pilot.click(SymbolGrid, offset=(8 + 3 * 2 + 1, 4))
        assert editor.text.startswith(
            f"{SYMBOL_GROUPS['Blocks'][0]}{SYMBOL_GROUPS['Lines'][1]}{SYMBOL_GROUPS['Double'][2]}"
        )
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, SymbolScreen)
        assert app.focused is editor

    _run(TTEApp(_EFFECTS, "abcd", effect="wipe"), script)


def test_colors_show_on_the_cursor_line() -> None:
    """Typed colors should show on the line with the cursor, not only after the cursor leaves it."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.editor
        editor.focus()
        editor.move_cursor((0, 4))
        editor.pen = colors.CellStyle(fg=Color("ff0000"), bg=Color("0000ff"))
        await pilot.press("x")
        await pilot.pause()
        styles = [segment.style for segment in editor.render_line(0) if segment.text.startswith("x")]
        assert styles
        style = styles[0]
        assert style is not None
        assert style.color is not None
        assert style.color.triplet is not None
        assert style.color.triplet.hex == "#ff0000"
        assert style.bgcolor is not None
        assert style.bgcolor.triplet is not None
        assert style.bgcolor.triplet.hex == "#0000ff"

    _run(TTEApp(_EFFECTS, "abcd\nefgh", effect="wipe"), script)


def test_text_colors_paint_the_selection_and_new_text() -> None:
    """A picked color should color the selection and typed text, and Clear should remove it."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.editor
        editor.focus()
        editor.selection = Selection((0, 0), (0, 2))
        app.query_one(TextToolbar).post_message(TextToolbar.PickColor("fg"))
        await pilot.pause()
        assert isinstance(app.screen, ColorScreen)
        app.screen.dismiss((Color("ff0000"),))
        await pilot.pause()
        red = colors.CellStyle(fg=Color("ff0000"))
        assert editor.color_styles == [red, red, None, None]
        assert editor.pen == red
        assert editor.selection.is_empty
        editor.move_cursor((0, 4))
        await pilot.press("x")
        await pilot.pause()
        assert editor.color_styles is not None
        assert editor.color_styles[-1] == red
        assert "\x1b[38;2;255;0;0m" in editor.colored_text() or "\x1b[38;5;" in editor.colored_text()
        editor.selection = Selection((0, 0), (0, 1))
        await pilot.click("#clear-color")
        await pilot.pause()
        assert editor.pen == colors.CellStyle()
        assert editor.color_styles == [None, red, None, None, red]
        # Typing after the red character stays plain once the colors are cleared.
        editor.move_cursor((0, 5))
        await pilot.press("z")
        await pilot.pause()
        assert editor.color_styles == [None, red, None, None, red, None]

    _run(TTEApp(_EFFECTS, "abcd", effect="wipe"), script)


def test_no_color_removes_one_layer() -> None:
    """No color in the picker should remove that layer from the selection and new text, keeping the other layer."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.editor
        red = Color("ff0000")
        blue = Color("0000ff")
        editor.attach_colors("abc", [colors.CellStyle(fg=red, bg=blue), colors.CellStyle(fg=red), None])
        editor.pen = colors.CellStyle(fg=red, bg=blue)
        editor.focus()
        editor.selection = Selection((0, 0), (0, 2))
        app.query_one(TextToolbar).post_message(TextToolbar.PickColor("fg"))
        await pilot.pause()
        assert isinstance(app.screen, ColorScreen)
        await pilot.click("#no-color")
        await pilot.pause()
        assert not isinstance(app.screen, ColorScreen)
        assert editor.color_styles == [colors.CellStyle(bg=blue), None, None]
        assert editor.pen == colors.CellStyle(bg=blue)

    _run(TTEApp(_EFFECTS, "abc", effect="wipe"), script)


def test_paint_skips_newlines_and_drops_empty_styles() -> None:
    """`paint` should leave newlines unstyled and turn empty styles into `None`."""
    red = colors.CellStyle(fg=Color("ff0000"))
    painted = colors.paint("a\nb", [None, None, None], 0, 3, lambda _style: red)
    assert painted == [red, None, red]
    assert colors.paint("ab", [red, red], 0, 1, lambda _style: colors.CellStyle()) == [None, red]


def test_paint_gradient_spreads_over_the_selection_box() -> None:
    """The gradient should run across the box around the selected characters and skip newlines."""
    red, blue = Color("ff0000"), Color("0000ff")
    gradient = Gradient(red, blue, steps=4)
    text = "ab\ncd"
    across = colors.paint_gradient(text, [None] * 5, 0, 5, gradient, Gradient.Direction.HORIZONTAL, "fg")
    assert [style.fg if style else None for style in across] == [red, blue, None, red, blue]
    down = colors.paint_gradient(text, [None] * 5, 1, 4, gradient, Gradient.Direction.VERTICAL, "bg")
    assert [style.bg if style else None for style in down] == [None, red, None, blue, None]


def test_gradient_chip_applies_and_builds_gradients() -> None:
    """The chip should color the selection, open the builder without one, and the builder should change the gradient."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.editor
        editor.focus()
        start, end = TextGradient().stops[0], TextGradient().stops[-1]
        editor.selection = Selection((0, 0), (0, 4))
        await pilot.click("#gradient", offset=(1, 0))
        await pilot.pause()
        styles = editor.color_styles
        assert styles is not None
        assert styles[0] == colors.CellStyle(fg=start)
        assert styles[3] == colors.CellStyle(fg=end)
        assert editor.selection.is_empty
        await pilot.click("#gradient", offset=(1, 0))
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, GradientScreen)
        screen.query_one("#layer", Select).value = "bg"
        screen.query_one("#steps", Input).value = "0"
        await pilot.pause()
        assert screen.query_one("#steps", Input).has_class("-invalid")
        assert screen.gradient.steps == TextGradient().steps
        await pilot.click("#apply")
        await pilot.pause()
        assert app._gradient.layer == "bg"
        editor.selection = Selection((0, 0), (0, 4))
        await pilot.click("#gradient", offset=(app.query_one("#gradient").size.width - 1, 0))
        await pilot.pause()
        assert isinstance(app.screen, GradientScreen)
        await pilot.click("#apply")
        await pilot.pause()
        styles = editor.color_styles
        assert styles is not None
        assert styles[0] == colors.CellStyle(fg=start, bg=start)

    _run(TTEApp(_EFFECTS, "abcd", effect="wipe"), script)
