"""Pilot tests for playback controls, the effect filter, commands, and the session."""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

from textual.widgets import Button, Checkbox, Input, OptionList

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.tui import frames
from terminaltexteffects.tui.app import CanvasView, OptionEditor, PanelSelect, TTEApp
from terminaltexteffects.tui.files import FileScreen
from terminaltexteffects.tui.screens import HelpScreen

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from textual.pilot import Pilot

_, _EFFECTS = build_parser(include_user_effects=False)
_SIZE = (110, 34)


def _run(app: TTEApp, script: Callable[[TTEApp, Pilot[None]], Awaitable[None]]) -> None:
    async def main() -> None:
        async with app.run_test(size=_SIZE) as pilot:
            await pilot.pause()
            await script(app, pilot)
            app._cancel_playback()

    asyncio.run(main())


async def _wait(pilot: Pilot[None], condition: Callable[[], bool], timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "timed out"
        await pilot.pause(0.02)


def _editor(app: TTEApp, scope: str, name: str) -> OptionEditor:
    return app.query_one(f"#option-{scope}-{name}", OptionEditor)


def test_play_pause_step_and_resume() -> None:
    """F5 should start, pause, and resume playback, and Right should step one frame while paused."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.press("f5")
        assert app.state == "playing"
        assert isinstance(app.focused, CanvasView)
        await _wait(pilot, lambda: app._frame_index >= 3)
        await pilot.press("space")
        assert app.state == "paused"
        assert str(app.query_one("#play", Button).label) == "▶ Play"
        await pilot.pause(0.1)
        paused_at = app._frame_index
        stream = app._stream
        assert isinstance(stream, frames.FrameStream)
        await _wait(pilot, lambda: not stream._queue.empty())
        await pilot.press("right")
        assert app._frame_index == paused_at + 1
        assert app.state == "paused"
        await pilot.press("f5")
        assert app.state == "playing"
        await pilot.press("escape")
        assert app.state == "editing"
        assert app._stream is None

    _run(TTEApp(_EFFECTS, "Hello\nworld", effect="decrypt"), script)


def test_loop_replays_the_kept_frames() -> None:
    """With Loop on, a finished effect should replay from the frames kept from the first run."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        _editor(app, "terminal", "frame_rate").query_one(Input).value = "0"
        app.query_one("#loop", Checkbox).value = True
        await pilot.pause()
        await pilot.press("f5")
        await _wait(pilot, lambda: app.state == "finished")
        assert app._recorded is not None
        await _wait(pilot, lambda: isinstance(app._stream, frames.RecordedFrames))
        assert app.state == "playing"
        app.query_one("#loop", Checkbox).value = False
        await _wait(pilot, lambda: app.state == "finished")
        await pilot.pause(1.2)
        assert app.state == "finished"

    _run(TTEApp(_EFFECTS, "Hi", effect="wipe"), script)


def test_auto_replay_follows_option_changes_without_taking_focus() -> None:
    """With Auto-replay on, editing an option should replay the effect and leave focus in the option."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        app.query_one("#auto-replay", Checkbox).value = True
        entry = _editor(app, "wipe", "wipe_delay").query_one(Input)
        entry.focus()
        entry.value = "1"
        # The replay waits for typing to settle, which a slow runner can outlast before the next check.
        await _wait(pilot, lambda: app.state == "playing")
        assert app.focused is entry
        app.query_one("#effects", OptionList).highlighted = sorted(_EFFECTS).index("decrypt")
        await _wait(pilot, lambda: app.effect_name == "decrypt" and app._playback_key is not None)
        await _wait(pilot, lambda: app._playback_key is not None and app._playback_key[0] == "decrypt")

    _run(TTEApp(_EFFECTS, "Hi", effect="wipe"), script)


def test_effect_filter_matches_names_and_descriptions() -> None:
    """Typing in the filter should list matching effects and highlight the first one."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.click("#effect-filter")
        await pilot.press(*"decrypt")
        await pilot.pause()
        effect_list = app.query_one("#effects", OptionList)
        assert app._listed == ["decrypt"]
        assert effect_list.option_count == 1
        assert app.effect_name == "decrypt"
        await pilot.press("down")
        assert app.focused is effect_list
        app.query_one("#effect-filter", Input).value = "zzz-no-match"
        await pilot.pause()
        assert effect_list.option_count == 0
        assert app.effect_name == "decrypt"

    _run(TTEApp(_EFFECTS, "Hi", effect="wipe"), script)


def test_random_effect_and_help() -> None:
    """F9 should play another effect, and F1 should open the help screen."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.press("f9")
        await pilot.pause()
        assert app.effect_name != "wipe"
        # Some effects play only a few frames on short text, so the effect may already have finished.
        assert app.state in ("playing", "finished")
        assert app._playback_key is not None
        assert app._playback_key[0] == app.effect_name
        assert not str(app.query_one("#stage").border_title).startswith("Failed")
        highlighted = app.query_one("#effects", OptionList).highlighted
        assert highlighted is not None
        assert app._listed[highlighted] == app.effect_name
        await pilot.press("escape", "f1")
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        assert not isinstance(app.screen, HelpScreen)

    _run(TTEApp(_EFFECTS, "Hi", effect="wipe"), script)


def test_pasted_command_sets_the_effect_options_and_text(tmp_path: Path) -> None:
    """Loading a command should select its effect, apply its options with CLI defaults elsewhere, and open its file."""
    text_file = tmp_path / "words.txt"
    text_file.write_text("from a file", encoding="utf-8")

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        _editor(app, "terminal", "tab_width").query_one(Input).value = "8"
        await pilot.pause()
        await app.apply_command(f"tte -i {text_file} --frame-rate 30 --canvas-width 0 wipe --wipe-delay 2 --bogus")
        await pilot.pause()
        assert app.effect_name == "wipe"
        assert _editor(app, "wipe", "wipe_delay").value == 2
        assert _editor(app, "terminal", "frame_rate").value == 30
        assert _editor(app, "terminal", "canvas_width").value == 0
        # Options left out take their CLI defaults, so the canvas height follows the text.
        assert _editor(app, "terminal", "canvas_height").value == -1
        assert _editor(app, "terminal", "tab_width").value == 4
        assert app.editor.text == "from a file"
        assert app.input_file == str(text_file)
        await pilot.press("f4")
        await pilot.pause()
        await pilot.click("#paste")
        await pilot.press(*"tte decrypt", "enter")
        await pilot.pause()
        assert app.effect_name == "decrypt"

    _run(TTEApp(_EFFECTS, "Hi", effect="beams"), script)


def test_session_is_restored(tmp_path: Path) -> None:
    """Quitting should save the session, and the next start should restore it."""
    path = tmp_path / "session.json"

    async def first(app: TTEApp, pilot: Pilot[None]) -> None:
        await app.apply_command("tte --frame-rate 30 wipe --wipe-delay 2")
        app.query_one("#loop", Checkbox).value = True
        app.editor.load_text("remember me")
        await pilot.pause()
        app.save_session()

    _run(TTEApp(_EFFECTS, "", session_path=path), first)

    async def second(app: TTEApp, pilot: Pilot[None]) -> None:  # noqa: ARG001
        assert app.effect_name == "wipe"
        assert _editor(app, "wipe", "wipe_delay").value == 2
        assert _editor(app, "terminal", "frame_rate").value == 30
        assert app.query_one("#loop", Checkbox).value is True
        assert app.editor.text == "remember me"

    _run(TTEApp(_EFFECTS, "", session_path=path), second)

    async def explicit(app: TTEApp, pilot: Pilot[None]) -> None:  # noqa: ARG001
        assert app.effect_name == "beams"
        assert app.editor.text == "given"

    _run(TTEApp(_EFFECTS, "given", effect="beams", session_path=path), explicit)


def test_fit_and_maximize_the_canvas() -> None:
    """Ctrl+T should fit the canvas to the text, and Ctrl+G should grow it to the whole area."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.press("ctrl+t")
        await pilot.pause()
        assert _editor(app, "terminal", "canvas_width").value == len("a longer line")
        assert _editor(app, "terminal", "canvas_height").value == 2
        await pilot.press("ctrl+g")
        await pilot.pause()
        assert _editor(app, "terminal", "canvas_width").value == 0
        assert _editor(app, "terminal", "canvas_height").value == 0

    _run(TTEApp(_EFFECTS, "short\na longer line", effect="wipe"), script)


def test_clicking_the_effect_returns_to_the_text() -> None:
    """Clicking the stage while an effect is shown should stop it and put the cursor at the clicked cell."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.press("f5")
        await _wait(pilot, lambda: app._frame_index > 0)
        await pilot.click("#canvas", offset=(3, 1))
        await pilot.pause()
        assert app.state == "editing"
        assert app.focused is app.editor
        assert app.editor.cursor_location == (1, 3)

    _run(TTEApp(_EFFECTS, "first\nsecond", effect="decrypt"), script)


def test_play_button_only_says_play_or_pause() -> None:
    """The play button should read Pause while playing and Play otherwise, and Open and Save should open dialogs."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        play = app.query_one("#play", Button)
        _editor(app, "terminal", "frame_rate").query_one(Input).value = "0"
        await pilot.pause()
        await pilot.press("f5")
        assert str(play.label) == "❚❚ Pause"
        await _wait(pilot, lambda: app.state == "finished")
        assert str(play.label) == "▶ Play"
        await pilot.click("#play")
        assert app.state in ("playing", "finished")
        await pilot.press("escape")
        assert str(play.label) == "▶ Play"
        assert not app.query("#replay")
        await pilot.click("#open")
        await pilot.pause()
        assert isinstance(app.screen, FileScreen)
        await pilot.press("escape")
        await pilot.pause(0.3)
        await pilot.click("#save")
        await pilot.pause()
        assert isinstance(app.screen, FileScreen)

    _run(TTEApp(_EFFECTS, "Hello\nworld", effect="decrypt"), script)


def test_dropdowns_stay_inside_the_options_panel() -> None:
    """An open dropdown should fit inside the options panel, opening above the field near the panel's bottom."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        panel = app.query_one("#effect-tab VerticalScroll")
        selects = [select for select in app.query(PanelSelect) if panel.region.contains_region(select.region)]
        assert selects
        for select in (selects[0], selects[-1]):
            select.expanded = True
            await pilot.pause()
            overlay = select.query_one("SelectOverlay")
            assert panel.region.contains_region(overlay.region), (select.id, overlay.region, panel.region)
            select.expanded = False
            await pilot.pause()

    _run(TTEApp(_EFFECTS, "Hi", effect="slide"), script)


def test_open_dropdowns_hide_option_tooltips() -> None:
    """An option's tooltip should not cover its dropdown while the list is open, and should return after."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        select = app.query(PanelSelect).first()
        editor = next(node for node in select.ancestors if isinstance(node, OptionEditor))
        tooltip = editor.tooltip
        assert tooltip is not None
        select.expanded = True
        await pilot.pause()
        assert editor.tooltip is None
        select.expanded = False
        await pilot.pause()
        assert editor.tooltip == tooltip

    _run(TTEApp(_EFFECTS, "Hi", effect="slide"), script)
