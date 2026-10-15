"""Copy text to and paste text from the system clipboard in the TUI.

Textual copies with the OSC 52 escape sequence, which many terminals ignore, including macOS Terminal and iTerm2
by default, and pastes only its own clipboard. The platform's clipboard commands are used as well, so copying and
pasting work in those terminals when the TUI runs on the same machine.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

_COMMANDS: dict[str, tuple[tuple[str, ...], ...]] = {
    "darwin": (("pbcopy",),),
    "win32": (("clip",),),
}
_UNIX_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("wl-copy",),
    ("xclip", "-selection", "clipboard"),
    ("xsel", "--clipboard", "--input"),
)
_TIMEOUT = 2.0


def clipboard_commands(platform: str = sys.platform) -> tuple[tuple[str, ...], ...]:
    """Return the clipboard commands to try on `platform`, in order."""
    return _COMMANDS.get(platform, _UNIX_COMMANDS)


def copy_with_system_command(text: str, platform: str = sys.platform) -> bool:
    """Copy `text` with the first clipboard command found on `platform`, and return whether one succeeded."""
    for command in clipboard_commands(platform):
        executable = shutil.which(command[0])
        if executable is None:
            continue
        try:
            subprocess.run(  # noqa: S603 (a fixed clipboard command found on PATH)
                [executable, *command[1:]],
                input=text.encode("utf-16" if platform == "win32" else "utf-8"),
                check=True,
                capture_output=True,
                timeout=_TIMEOUT,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        return True
    return False


_PASTE_COMMANDS: dict[str, tuple[tuple[str, ...], ...]] = {
    "darwin": (("pbpaste",),),
    "win32": (("powershell", "-NoProfile", "-Command", "Get-Clipboard -Raw"),),
}
_UNIX_PASTE_COMMANDS: tuple[tuple[str, ...], ...] = (
    ("wl-paste", "--no-newline"),
    ("xclip", "-selection", "clipboard", "-out"),
    ("xsel", "--clipboard", "--output"),
)


def paste_commands(platform: str = sys.platform) -> tuple[tuple[str, ...], ...]:
    """Return the commands that print the clipboard on `platform`, in order."""
    return _PASTE_COMMANDS.get(platform, _UNIX_PASTE_COMMANDS)


def paste_with_system_command(platform: str = sys.platform) -> str | None:
    """Return the system clipboard's text from the first command found on `platform`, or `None` if none worked."""
    for command in paste_commands(platform):
        executable = shutil.which(command[0])
        if executable is None:
            continue
        try:
            result = subprocess.run(  # noqa: S603 (a fixed clipboard command found on PATH)
                [executable, *command[1:]],
                check=True,
                capture_output=True,
                timeout=_TIMEOUT,
            )
        except (OSError, subprocess.SubprocessError):
            continue
        text = result.stdout.decode("utf-8", errors="replace")
        return text.replace("\r\n", "\n") if platform == "win32" else text
    return None
