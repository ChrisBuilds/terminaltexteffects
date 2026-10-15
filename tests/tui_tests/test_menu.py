"""Pilot tests for the right-click context menu and clipboard paste."""

from __future__ import annotations

import asyncio
import typing

from textual import events
from textual.widgets import OptionList
from textual.widgets.text_area import Selection

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.tui import clipboard
from terminaltexteffects.tui.app import TTEApp
from terminaltexteffects.tui.menu import ContextMenu
from terminaltexteffects.tui.picker import ColorScreen
from terminaltexteffects.tui.toolbar import SymbolScreen

if typing.TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    import pytest
    from textual.pilot import Pilot

_, _EFFECTS = build_parser(include_user_effects=False)


def _run(app: TTEApp, script: Callable[[TTEApp, Pilot[None]], Awaitable[None]]) -> None:
    async def main() -> None:
        async with app.run_test(size=(110, 34)) as pilot:
            await pilot.pause()
            await script(app, pilot)
            app._cancel_playback()

    asyncio.run(main())


async def _choose(app: TTEApp, pilot: Pilot[None], action: str) -> None:
    await pilot.click("#editor", offset=(6, 0), button=3)
    await pilot.pause()
    screen = app.screen
    assert isinstance(screen, ContextMenu)
    menu = screen.query_one(OptionList)
    menu.highlighted = menu.get_option_index(action)
    await pilot.press("enter")
    await pilot.pause()


def test_right_click_keeps_the_selection_and_offers_actions(monkeypatch: pytest.MonkeyPatch) -> None:
    """A right click should open the menu without losing the selection, and its entries should act on the text."""
    copied: list[str] = []
    monkeypatch.setattr(clipboard, "copy_with_system_command", lambda text: copied.append(text) or True)
    monkeypatch.setattr(clipboard, "paste_with_system_command", lambda: "PASTED")

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.editor
        editor.focus()
        editor.selection = Selection((0, 0), (0, 5))
        await pilot.click("#editor", offset=(6, 0), button=3)
        await pilot.pause()
        screen = app.screen
        assert isinstance(screen, ContextMenu)
        assert editor.selection == Selection((0, 0), (0, 5))
        assert screen.query_one(OptionList).get_option("stop").disabled
        await pilot.press("escape")
        await pilot.pause()
        await _choose(app, pilot, "cut")
        assert editor.text == " world"
        assert copied == ["Hello"]
        await _choose(app, pilot, "paste")
        assert editor.text.startswith("PASTED")
        await _choose(app, pilot, "select_all")
        assert editor.selected_text == editor.text
        await _choose(app, pilot, "fg")
        assert isinstance(app.screen, ColorScreen)
        await pilot.press("escape")
        await pilot.pause()
        await _choose(app, pilot, "symbols")
        assert isinstance(app.screen, SymbolScreen)

    _run(TTEApp(_EFFECTS, "Hello world", effect="wipe"), script)


def test_paste_falls_back_to_the_app_clipboard(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ctrl+V should paste the app's own clipboard when the system clipboard can't be read."""
    monkeypatch.setattr(clipboard, "paste_with_system_command", lambda: None)

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        app._clipboard = "local"
        editor = app.editor
        editor.focus()
        editor.move_cursor((0, 2))
        await pilot.press("ctrl+v")
        assert editor.text == "ablocal"

    _run(TTEApp(_EFFECTS, "ab", effect="wipe"), script)


def test_paste_commands_per_platform() -> None:
    """Each platform should have its clipboard-reading command first."""
    assert clipboard.paste_commands("darwin") == (("pbpaste",),)
    assert clipboard.paste_commands("linux")[0] == ("wl-paste", "--no-newline")


def test_cut_and_paste_keep_colors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Text cut or copied in the editor should keep its colors when pasted back, by key or bracketed paste."""
    system: list[str] = []
    monkeypatch.setattr(clipboard, "copy_with_system_command", lambda text: system.append(text) or True)
    monkeypatch.setattr(clipboard, "paste_with_system_command", lambda: system[-1] if system else None)

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.editor
        red = editor.color_styles[0] if editor.color_styles else None
        assert red is not None
        editor.focus()
        editor.selection = Selection((0, 0), (0, 3))
        await pilot.press("ctrl+x")
        await pilot.pause()
        assert editor.text == " text"
        editor.move_cursor((0, 5))
        await pilot.press("ctrl+v")
        await pilot.pause()
        assert editor.text == " textred"
        assert editor.color_styles == [None] * 5 + [red] * 3
        editor.selection = Selection((0, 5), (0, 8))
        await pilot.press("ctrl+c")
        editor.move_cursor((0, 0))
        app.post_message(events.Paste("red"))
        await pilot.pause()
        assert editor.text == "red textred"
        assert editor.color_styles == [red] * 3 + [None] * 5 + [red] * 3

    _run(TTEApp(_EFFECTS, "\x1b[31mred\x1b[0m text", effect="wipe"), script)


def test_menu_highlight_follows_the_mouse() -> None:
    """Moving the mouse over an entry should highlight it."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.click("#editor", offset=(2, 0), button=3)
        await pilot.pause()
        menu = app.screen.query_one(OptionList)
        await pilot.hover(OptionList, offset=(3, menu.get_option_index("select_all") + 1))
        await pilot.pause()
        assert menu.highlighted == menu.get_option_index("select_all")

    _run(TTEApp(_EFFECTS, "Hello", effect="wipe"), script)
