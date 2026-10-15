"""Tests for the TUI export dialog."""

from __future__ import annotations

import asyncio
import typing

from textual.widgets import Input, Select

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.tui.app import TTEApp
from terminaltexteffects.tui.files import FileScreen
from terminaltexteffects.utils import export

if typing.TYPE_CHECKING:
    import pytest

_, _EFFECTS = build_parser(include_user_effects=False)


def test_export_dialog_offers_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    """The export dialog should switch the suffix with the format and refuse a format whose Pillow is missing."""
    monkeypatch.setattr(export, "pillow_available", lambda: False)

    async def main() -> None:
        app = TTEApp(_EFFECTS, "Hi", effect="wipe")
        async with app.run_test(size=(110, 34)) as pilot:
            await pilot.pause()
            await pilot.click("#export")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, FileScreen)
            path = screen.query_one("#path", Input)
            assert path.value == "wipe.tterec"
            screen.query_one("#format", Select).value = ".gif"
            await pilot.pause()
            assert path.value == "wipe.gif"
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is screen
            assert "export needs" in str(screen.query_one("#message").render())
            path.value = "wipe.tterec"
            await pilot.pause()
            assert screen.query_one("#format", Select).value == ".tterec"

    asyncio.run(main())
