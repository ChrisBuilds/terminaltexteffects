"""Pilot tests for the Textual interface."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.widgets import Checkbox, Input, OptionList, TextArea

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.engine._recording import RecordingReader
from terminaltexteffects.tui.app import CanvasView, CommandScreen, OptionEditor, PathScreen, TTEApp

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from textual.pilot import Pilot

_, _EFFECTS = build_parser(include_user_effects=False)
_SIZE = (100, 34)


def _run(app: TTEApp, script: Callable[[TTEApp, Pilot[None]], Awaitable[None]]) -> None:
    """Run `script` against `app` in a headless terminal."""

    async def main() -> None:
        async with app.run_test(size=_SIZE) as pilot:
            await pilot.pause()
            await script(app, pilot)

    asyncio.run(main())


def _editor(app: TTEApp, scope: str, name: str) -> OptionEditor:
    return app.query_one(f"#option-{scope}-{name}", OptionEditor)


async def _set_frame_rate(app: TTEApp, pilot: Pilot[None], value: str) -> None:
    _editor(app, "terminal", "frame_rate").query_one(Input).value = value
    await pilot.pause()


def test_effect_list_shows_every_effect_and_its_options() -> None:
    """Highlighting an effect should show one editor per option."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        effect_list = app.query_one("#effects", OptionList)
        assert effect_list.option_count == len(_EFFECTS)
        effect_list.highlighted = sorted(_EFFECTS).index("wipe")
        await pilot.pause()
        assert app.effect_name == "wipe"
        names = {editor.option.name for editor in app.query(OptionEditor) if editor.scope == "wipe"}
        assert names == {option.name for option in app._scope_fields("wipe")}

    _run(TTEApp(_EFFECTS), script)


def test_play_renders_over_the_text_and_escape_returns_to_editing() -> None:
    """Playing should show frames sized to the text area and keep the last frame until Escape."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await _set_frame_rate(app, pilot, "0")
        await pilot.press("f5")
        assert app.state in {"playing", "finished"}
        assert app.query_one("#stage").has_class("-playing")
        while app.state == "playing":
            await pilot.pause(0.05)
        canvas = app.query_one("#canvas", CanvasView)
        width, height = app._canvas_size()
        assert len(canvas._strips) == height
        assert canvas._strips[0].text.rstrip() == "Hello"
        assert canvas._strips[0].cell_length == width
        await pilot.press("escape")
        assert app.state == "editing"
        assert app.editor.has_focus
        assert app.editor.text == "Hello\nworld"

    _run(TTEApp(_EFFECTS, "Hello\nworld", effect="wipe"), script)


def test_invalid_option_blocks_play_until_fixed() -> None:
    """Invalid editor text should be reported and keep the effect from playing."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        typing_speed = _editor(app, "decrypt", "typing_speed")
        typing_speed.query_one(Input).value = "0"
        await pilot.pause()
        assert typing_speed.error is not None
        assert "invalid" in str(app.query_one("#stage").border_subtitle)
        await pilot.press("f5")
        assert app.state == "editing"
        typing_speed.query_one(Input).value = "3"
        await pilot.pause()
        assert app._values["decrypt"]["typing_speed"] == 3
        assert "invalid" not in str(app.query_one("#stage").border_subtitle)

    _run(TTEApp(_EFFECTS, "text", effect="decrypt"), script)


def test_values_are_kept_per_effect_and_reset() -> None:
    """Edited values should survive switching effects and return to defaults on reset."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        _editor(app, "terminal", "wrap_text").query_one(Checkbox).value = True
        _editor(app, "decrypt", "typing_speed").query_one(Input).value = "5"
        await pilot.pause()
        effect_list = app.query_one("#effects", OptionList)
        effect_list.highlighted = sorted(_EFFECTS).index("wipe")
        await pilot.pause()
        effect_list.highlighted = sorted(_EFFECTS).index("decrypt")
        await pilot.pause()
        assert _editor(app, "decrypt", "typing_speed").query_one(Input).value == "5"
        await pilot.press("f6")
        await pilot.pause()
        assert _editor(app, "decrypt", "typing_speed").value == 2
        assert _editor(app, "terminal", "wrap_text").value is False
        assert not app._values.get("decrypt")

    _run(TTEApp(_EFFECTS, "text", effect="decrypt"), script)


def test_command_dialog_shows_the_cli_command() -> None:
    """The command dialog should show the CLI command for the current options."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        _editor(app, "wipe", "wipe_delay").query_one(Input).value = "3"
        await pilot.pause()
        await pilot.press("f4")
        await pilot.pause()
        assert isinstance(app.screen, CommandScreen)
        assert app.screen.command == (
            "tte --input-file in.txt --canvas-width 0 --canvas-height 0 --anchor-canvas nw --anchor-text nw "
            "wipe --wipe-delay 3"
        )

    _run(TTEApp(_EFFECTS, "text", input_file="in.txt", effect="wipe"), script)


def test_open_and_save_files(tmp_path: Path) -> None:
    """Text should load from and save to files, keeping input colors when asked."""
    source = tmp_path / "in.txt"
    source.write_text("\x1b[31mred\x1b[0m text", encoding="utf-8")
    target = tmp_path / "out.txt"

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.press("f2")
        await pilot.pause()
        assert isinstance(app.screen, PathScreen)
        app.screen.query_one("#path", Input).value = str(source)
        await pilot.press("enter")
        await pilot.pause()
        assert app.editor.text == "red text"
        assert app.editor.color_styles is not None
        await pilot.press("f3")
        await pilot.pause()
        assert app.screen.query_one("#path", Input).value == str(source)
        assert app.screen.query_one("#checkbox", Checkbox).value is True
        app.screen.query_one("#path", Input).value = str(target)
        await pilot.press("enter")
        await pilot.pause()
        assert target.read_text(encoding="utf-8") == "\x1b[38;5;1mred\x1b[0m text"
        assert app.input_file == str(target)

    _run(TTEApp(_EFFECTS, effect="wipe"), script)


def test_colored_input_keeps_colors_through_edits() -> None:
    """Edits should keep input colors on unchanged characters and pass them to the effect."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        editor = app.query_one("#editor", TextArea)
        editor.insert("> ", (0, 0))
        await pilot.pause()
        assert app.editor.text == "> red text"
        assert app.editor.colored_text() == "> \x1b[38;5;1mred\x1b[0m text"

    _run(TTEApp(_EFFECTS, "\x1b[31mred\x1b[0m text", effect="wipe"), script)


def test_record_writes_a_recording(tmp_path: Path) -> None:
    """Recording should render the configured effect to a playable recording file."""
    target = tmp_path / "wipe.tterec"

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.press("f8")
        await pilot.pause()
        app.screen.query_one("#path", Input).value = str(target)
        await pilot.press("enter")
        await app.workers.wait_for_complete()
        await pilot.pause()
        width, height = app._canvas_size()
        with RecordingReader(target) as reader:
            header = reader.header
            assert (header.width, header.height) == (width, height)
            assert reader.validate() > 0

    _run(TTEApp(_EFFECTS, "Hello", effect="wipe"), script)


def test_record_needs_a_frame_rate() -> None:
    """Recording should refuse an unlimited frame rate instead of asking for a path."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await _set_frame_rate(app, pilot, "0")
        await pilot.press("f8")
        await pilot.pause()
        assert not isinstance(app.screen, PathScreen)

    _run(TTEApp(_EFFECTS, "Hello", effect="wipe"), script)


def test_errors_clear_when_returning_to_an_effect() -> None:
    """An invalid value left on an effect should not block it after switching away and back."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        _editor(app, "wipe", "wipe_delay").query_one(Input).value = "-1"
        await pilot.pause()
        assert app._current_errors()
        effect_list = app.query_one("#effects", OptionList)
        effect_list.highlighted = sorted(_EFFECTS).index("decrypt")
        await pilot.pause()
        effect_list.highlighted = sorted(_EFFECTS).index("wipe")
        await pilot.pause()
        assert not app._current_errors()

    _run(TTEApp(_EFFECTS, "text", effect="wipe"), script)


def test_app_shortcuts_wait_while_a_dialog_is_open() -> None:
    """Shortcuts other than Quit should not act behind an open dialog."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        await pilot.press("f2")
        await pilot.pause()
        await pilot.press("f5")
        await pilot.pause()
        assert isinstance(app.screen, PathScreen)
        assert app.state == "editing"

    _run(TTEApp(_EFFECTS, "text", effect="wipe"), script)


def test_command_omits_input_file_after_edits() -> None:
    """An edited text no longer matches its file, so the command should not read that file."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        app.query_one("#editor", TextArea).insert("more ", (0, 0))
        await pilot.pause()
        await pilot.press("f4")
        await pilot.pause()
        assert isinstance(app.screen, CommandScreen)
        assert "--input-file" not in app.screen.command

    _run(TTEApp(_EFFECTS, "text", input_file="in.txt", effect="wipe"), script)


def test_tabs_are_kept_and_follow_the_tab_width() -> None:
    """Tabs should stay in the text and display at the configured tab width."""

    async def script(app: TTEApp, pilot: Pilot[None]) -> None:
        assert app.editor.text == "a\tb"
        assert app.editor.indent_width == 4
        _editor(app, "terminal", "tab_width").query_one(Input).value = "8"
        await pilot.pause()
        assert app.editor.indent_width == 8

    _run(TTEApp(_EFFECTS, "a\tb", effect="wipe"), script)
