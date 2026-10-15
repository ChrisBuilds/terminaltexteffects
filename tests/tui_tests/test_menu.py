"""Pilot tests for the right-click context menu and clipboard paste."""

from __future__ import annotations

import asyncio
import typing

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
