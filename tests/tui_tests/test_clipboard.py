"""Tests for copying to the system clipboard."""

from __future__ import annotations

import subprocess
import typing

from terminaltexteffects.tui import clipboard

if typing.TYPE_CHECKING:
    import pytest


def test_platform_commands() -> None:
    """On macOS, copying should use pbcopy, on Windows clip, and elsewhere the Wayland and X11 tools."""
    assert clipboard.clipboard_commands("darwin") == (("pbcopy",),)
    assert clipboard.clipboard_commands("win32") == (("clip",),)
    assert clipboard.clipboard_commands("linux")[0] == ("wl-copy",)


def test_copy_uses_the_first_working_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """The text should go to the first command found on PATH that succeeds."""
    calls: list[tuple[list[str], bytes]] = []

    def run(args: list[str], **kwargs: typing.Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((args, kwargs["input"]))
        if args[0].endswith("wl-copy"):
            raise subprocess.CalledProcessError(1, args)
        return subprocess.CompletedProcess(args, 0)

    monkeypatch.setattr(clipboard.shutil, "which", lambda name: None if name == "xsel" else f"/usr/bin/{name}")
    monkeypatch.setattr(clipboard.subprocess, "run", run)
    assert clipboard.copy_with_system_command("tte wipe", "linux")
    assert calls == [
        (["/usr/bin/wl-copy"], b"tte wipe"),
        (["/usr/bin/xclip", "-selection", "clipboard"], b"tte wipe"),
    ]


def test_copy_reports_when_no_command_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a clipboard command, copying should report failure."""
    monkeypatch.setattr(clipboard.shutil, "which", lambda _name: None)
    assert not clipboard.copy_with_system_command("tte wipe", "darwin")
