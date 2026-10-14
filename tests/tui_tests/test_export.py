"""Tests for recording to GIF and WebP from the TUI, without running external tools."""

from __future__ import annotations

import asyncio
import typing
from pathlib import Path

from textual.widgets import Input, Select

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.engine._recording import RecordingHeader, RecordingWriter
from terminaltexteffects.tui import export
from terminaltexteffects.tui.app import TTEApp
from terminaltexteffects.tui.files import FileScreen

if typing.TYPE_CHECKING:
    import pytest

_, _EFFECTS = build_parser(include_user_effects=False)
_GIF, _WEBP = export.FORMATS[1], export.FORMATS[2]


def _write_recording(path: Path) -> None:
    with RecordingWriter(path, RecordingHeader("test", 2, 1, 10)) as writer:
        writer.begin_segment("test")
        writer.write_frame("ab")
        writer.write_frame("cd")


def test_formats_follow_the_suffix() -> None:
    """The suffix should pick the format, and unknown suffixes should record a tterec."""
    assert export.format_for(Path("a.GIF")) is _GIF
    assert export.format_for(Path("a.webp")) is _WEBP
    assert export.format_for(Path("a.cast")) is export.FORMATS[0]


def test_missing_tools_are_named_with_their_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """A format whose commands are missing should say which and where to get them."""
    monkeypatch.setattr(export.shutil, "which", lambda name: None if name == "gif2webp" else f"/bin/{name}")
    assert export.format_problem(_GIF) is None
    assert export.format_problem(export.FORMATS[0]) is None
    assert export.format_problem(_WEBP) == "WebP needs gif2webp from libwebp on PATH."


def test_webp_export_renders_a_gif_with_agg_then_converts_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """WebP output should render the canvas cast with agg and convert the GIF with gif2webp."""
    commands: list[list[str]] = []

    def run(command: list[str]) -> None:
        commands.append(command)
        if command[0] == "agg":
            assert Path(command[-2]).read_text(encoding="utf-8").startswith('{"version": 2')

    monkeypatch.setattr(export, "_run", run)
    recording = tmp_path / "effect.tterec"
    _write_recording(recording)
    export.export_recording(recording, tmp_path / "out.webp", _WEBP, fps=30)
    assert [command[0] for command in commands] == ["agg", "gif2webp"]
    assert "--fps-cap" in commands[0]
    assert commands[0][commands[0].index("--fps-cap") + 1] == "30"
    assert commands[1][-1] == str(tmp_path / "out.webp")


def test_record_dialog_offers_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    """The record dialog should switch the suffix with the format and refuse a format whose tools are missing."""
    monkeypatch.setattr(export.shutil, "which", lambda _name: None)

    async def main() -> None:
        app = TTEApp(_EFFECTS, "Hi", effect="wipe")
        async with app.run_test(size=(110, 34)) as pilot:
            await pilot.pause()
            await pilot.click("#record")
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
            assert "agg" in str(screen.query_one("#message").render())
            path.value = "wipe.tterec"
            await pilot.pause()
            assert screen.query_one("#format", Select).value == ".tterec"

    asyncio.run(main())
