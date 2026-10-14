"""Pilot tests for the text toolbar: text colors and symbol palettes."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.widgets.text_area import Selection

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.tui import colors
from terminaltexteffects.tui.app import TTEApp
from terminaltexteffects.tui.picker import ColorScreen
from terminaltexteffects.tui.toolbar import SYMBOL_GROUPS, SymbolStrip, TextToolbar
from terminaltexteffects.utils.graphics import Color

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


def test_symbols_insert_at_the_cursor_and_replace_the_selection() -> None:
    """Clicking a symbol should insert it at the cursor, or replace the selected text, and keep editor focus."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.editor
        editor.focus()
        editor.move_cursor((0, 2))
        await pilot.click("#symbols", offset=(0, 0))
        assert editor.text == "ab█cd"
        assert editor.cursor_location == (0, 3)
        assert app.focused is editor
        await pilot.pause(0.25)
        await pilot.click("#group-lines")
        assert app.query_one(SymbolStrip).symbols == SYMBOL_GROUPS["Lines"]
        editor.selection = Selection((0, 0), (0, 2))
        await pilot.click("#symbols", offset=(2, 0))
        assert editor.text == f"{SYMBOL_GROUPS['Lines'][1]}█cd"

    _run(TTEApp(_EFFECTS, "abcd", effect="wipe"), script)


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
        editor.move_cursor((0, 4))
        await pilot.press("x")
        await pilot.pause()
        assert editor.color_styles is not None
        assert editor.color_styles[-1] == red
        assert "\x1b[38;2;255;0;0m" in editor.colored_text() or "\x1b[38;5;" in editor.colored_text()
        editor.selection = Selection((0, 0), (0, 1))
        await pilot.click("#clear-color")
        await pilot.pause()
        assert editor.pen is None
        assert editor.color_styles == [None, red, None, None, red]

    _run(TTEApp(_EFFECTS, "abcd", effect="wipe"), script)


def test_paint_skips_newlines_and_drops_empty_styles() -> None:
    """`paint` should leave newlines unstyled and turn empty styles into `None`."""
    red = colors.CellStyle(fg=Color("ff0000"))
    painted = colors.paint("a\nb", [None, None, None], 0, 3, lambda _style: red)
    assert painted == [red, None, red]
    assert colors.paint("ab", [red, red], 0, 1, lambda _style: colors.CellStyle()) == [None, red]
