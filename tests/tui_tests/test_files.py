"""Tests for the TUI file dialog."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from textual.app import App
from textual.widgets import DirectoryTree, Input, Static

from terminaltexteffects.tui.files import FileScreen

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from pathlib import Path

    from textual.pilot import Pilot


def _run(make_screen: Callable[[], FileScreen], script: Callable[[FileScreen, Pilot[None]], Awaitable[None]]) -> list:
    """Run `script` with the screen from `make_screen` open and return the values it was dismissed with.

    The screen is created inside the event loop, which widgets need on Python 3.9.
    """
    results: list = []

    class Host(App[None]):
        def on_mount(self) -> None:
            self.push_screen(make_screen(), results.append)

    async def main() -> None:
        app = Host()
        async with app.run_test(size=(100, 34)) as pilot:
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, FileScreen)
            await script(screen, pilot)

    asyncio.run(main())
    return results


def _message(screen: FileScreen) -> str:
    return str(screen.query_one("#message", Static).render())


def test_open_browses_the_folder_of_the_initial_path(tmp_path: Path) -> None:
    """The tree should start in the initial file's folder, and choosing a file twice should open it."""
    (tmp_path / "notes.txt").write_text("hi", encoding="utf-8")
    (tmp_path / ".hidden").write_text("", encoding="utf-8")

    async def script(screen: FileScreen, pilot: Pilot[None]) -> None:
        tree = screen.query_one(DirectoryTree)
        assert str(tree.path) == str(tmp_path)
        target = tmp_path / "notes.txt"
        tree.post_message(DirectoryTree.FileSelected(tree.root, target))
        await pilot.pause()
        assert screen.query_one("#path", Input).value == str(target)
        tree.post_message(DirectoryTree.FileSelected(tree.root, target))
        await pilot.pause()

    results = _run(lambda: FileScreen("Open", str(tmp_path / "missing.txt"), mode="open"), script)
    assert results == [(str(tmp_path / "notes.txt"), False)]


def test_open_rejects_missing_files_and_browses_folders(tmp_path: Path) -> None:
    """Opening a missing file should explain why, and submitting a folder should browse it."""
    (tmp_path / "sub").mkdir()

    async def script(screen: FileScreen, pilot: Pilot[None]) -> None:
        path = screen.query_one("#path", Input)
        path.value = str(tmp_path / "nope.txt")
        await pilot.press("enter")
        await pilot.pause()
        assert "is not a file" in _message(screen)
        path.value = str(tmp_path / "sub")
        await pilot.press("enter")
        await pilot.pause()
        assert str(screen.query_one(DirectoryTree).path) == str(tmp_path / "sub")
        await pilot.press("escape")

    assert _run(lambda: FileScreen("Open", "", mode="open"), script) == [None]


def test_save_asks_before_replacing_a_file(tmp_path: Path) -> None:
    """Saving over an existing file should need a second confirmation."""
    existing = tmp_path / "out.txt"
    existing.write_text("old", encoding="utf-8")

    async def script(screen: FileScreen, pilot: Pilot[None]) -> None:
        await pilot.press("enter")
        await pilot.pause()
        assert "already exists" in _message(screen)
        assert screen.app.screen is screen
        await pilot.press("enter")
        await pilot.pause()

    assert _run(lambda: FileScreen("Save", str(existing), mode="save"), script) == [(str(existing), False)]


def test_save_keeps_the_file_name_when_choosing_a_folder(tmp_path: Path) -> None:
    """Choosing a folder in the tree while saving should keep the typed file name."""
    folder = tmp_path / "sub"
    folder.mkdir()

    async def script(screen: FileScreen, pilot: Pilot[None]) -> None:
        tree = screen.query_one(DirectoryTree)
        tree.post_message(DirectoryTree.DirectorySelected(tree.root, folder))
        await pilot.pause()
        assert screen.query_one("#path", Input).value == str(folder / "out.txt")

    _run(lambda: FileScreen("Save", str(tmp_path / "out.txt"), mode="save"), script)


def test_hidden_files_toggle(tmp_path: Path) -> None:
    """Dot files should be hidden until shown with Ctrl+T."""
    (tmp_path / ".hidden").write_text("", encoding="utf-8")
    (tmp_path / "shown").write_text("", encoding="utf-8")
    entries = list(tmp_path.iterdir())

    async def script(screen: FileScreen, pilot: Pilot[None]) -> None:
        tree = screen.file_tree
        assert [path.name for path in tree.filter_paths(entries)] == ["shown"]
        await pilot.press("ctrl+t")
        await pilot.pause()
        assert sorted(path.name for path in tree.filter_paths(entries)) == [".hidden", "shown"]

    _run(lambda: FileScreen("Open", str(tmp_path / "shown"), mode="open"), script)
