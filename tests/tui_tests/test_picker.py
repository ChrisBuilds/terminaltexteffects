"""Tests for the TUI color picker."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.widgets import Input

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.tui import picker
from terminaltexteffects.tui.app import OptionEditor, TTEApp
from terminaltexteffects.utils.graphics import Color

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from textual.pilot import Pilot

_, _EFFECTS = build_parser(include_user_effects=False)


def _run(app: TTEApp, script: Callable[[TTEApp, Pilot[None]], Awaitable[None]]) -> None:
    async def main() -> None:
        async with app.run_test(size=(130, 40)) as pilot:
            await pilot.pause()
            await script(app, pilot)

    asyncio.run(main())


def _editor(app: TTEApp, scope: str, name: str) -> OptionEditor:
    return app.query_one(f"#option-{scope}-{name}", OptionEditor)


async def _open_picker(app: TTEApp, pilot: Pilot[None], editor: OptionEditor) -> picker.ColorScreen:
    editor.query_one(Input).focus()
    await pilot.press("f7")
    await pilot.pause()
    assert isinstance(app.screen, picker.ColorScreen)
    return app.screen


def test_palette_holds_every_xterm_color_once() -> None:
    """The palette layout should place each of the 256 XTerm colors in one cell."""
    assert sorted(picker._PALETTE.values()) == list(range(256))


def test_hls_round_trip() -> None:
    """Converting to HLS and back should return the same color."""
    for value in ("8a008a", "00d1ff", "ffffff", "000000", "123456"):
        assert picker.hls_to_color(*picker.color_to_hls(Color(value))) == Color(value)


def test_contrast_color_picks_readable_text() -> None:
    """Text on light colors should be black and text on dark colors white."""
    assert picker.contrast_color(Color("ffffff")) == "000000"
    assert picker.contrast_color(Color("000080")) == "ffffff"


def test_palette_pick_and_new_stop_update_a_gradient_option() -> None:
    """Picking a palette color and adding a stop should write the new stops to the option."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = _editor(app, "beams", "final_gradient_stops")
        screen = await _open_picker(app, pilot, editor)
        assert [stop.rgb_color for stop in screen.stops] == ["8a008a", "00d1ff", "ffffff"]
        # Move the palette cursor from black (0) to xterm color 2 and pick it for the first stop.
        await pilot.press("right", "right", "enter")
        await pilot.click("#add")
        await pilot.press("ctrl+s")
        await pilot.pause()
        assert editor.value == (Color(2), Color(2), Color("00d1ff"), Color("ffffff"))
        assert editor.query_one(Input).value == "2 2 00d1ff ffffff"

    _run(TTEApp(_EFFECTS, "text", effect="beams"), script)


def test_hex_entry_sets_a_single_color_option() -> None:
    """Typing a hex value and pressing Enter should set a single-color option."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = _editor(app, "blackhole", "blackhole_color")
        screen = await _open_picker(app, pilot, editor)
        assert not screen.multiple
        hex_input = screen.query_one("#hex", Input)
        hex_input.value = "zz"
        await pilot.pause()
        assert hex_input.has_class("-invalid")
        hex_input.value = "#ff8800"
        await pilot.pause()
        hex_input.focus()
        await pilot.press("enter")
        await pilot.pause()
        assert editor.value == Color("ff8800")

    _run(TTEApp(_EFFECTS, "text", effect="blackhole"), script)


def test_channel_bars_mix_colors_and_cancel_keeps_the_value() -> None:
    """Moving a channel bar should change the color, and cancelling should leave the option unchanged."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = _editor(app, "blackhole", "blackhole_color")
        screen = await _open_picker(app, pilot, editor)
        before = screen.color
        screen.query_one("#lightness", picker.ChannelBar).focus()
        await pilot.press("shift+left")
        await pilot.pause()
        assert screen.color != before
        assert screen.color.xterm_color is None
        await pilot.press("escape")
        await pilot.pause()
        assert not isinstance(app.screen, picker.ColorScreen)
        assert editor.value == Color("ffffff")

    _run(TTEApp(_EFFECTS, "text", effect="blackhole"), script)


def test_picker_is_offered_only_for_color_options() -> None:
    """F7 should do nothing on options that are not colors."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        _editor(app, "beams", "beam_delay").query_one(Input).focus()
        await pilot.press("f7")
        await pilot.pause()
        assert not isinstance(app.screen, picker.ColorScreen)

    _run(TTEApp(_EFFECTS, "text", effect="beams"), script)
