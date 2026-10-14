"""Interactive Textual interface for composing text and previewing effects.

The interface needs the optional `tui` extra (`pip install terminaltexteffects[tui]`), which installs Textual.
Importing this package does not import Textual; `run` imports it when the interface starts.
"""

from __future__ import annotations

import importlib.util
import os
import sys
import typing

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_config import BaseConfig
    from terminaltexteffects.engine.base_effect import BaseEffect

INSTALL_HINT = "The interactive interface needs Textual. Install it with: pip install 'terminaltexteffects[tui]'"


def is_available() -> bool:
    """Return whether Textual is installed."""
    return importlib.util.find_spec("textual") is not None


def attach_keyboard() -> None:
    """Point standard input at the controlling terminal after piped input has been read.

    Textual reads keys from standard input, so after `echo text | tte` it must be reattached to the terminal, as
    pagers such as `less` do.

    Raises:
        OSError: If the controlling terminal cannot be opened.

    """
    if sys.stdin is not None and sys.stdin.isatty():
        return
    terminal_path = "CONIN$" if os.name == "nt" else "/dev/tty"
    terminal_fd = os.open(terminal_path, os.O_RDWR if os.name == "nt" else os.O_RDONLY)
    os.dup2(terminal_fd, 0)
    os.close(terminal_fd)
    sys.stdin = sys.__stdin__ = open(0, encoding="utf-8", closefd=False)  # noqa: SIM115


def run(
    effect_resource_map: dict[str, tuple[type[BaseEffect], type[BaseConfig]]],
    text: str = "",
    input_file: str | None = None,
    effect: str | None = None,
) -> None:
    """Run the interactive interface until the user quits.

    Args:
        effect_resource_map (dict[str, tuple[type[BaseEffect], type[BaseConfig]]]): Effect command names mapped to
            their effect and config classes.
        text (str): Initial text, which may contain ANSI colors.
        input_file (str | None): File the text was read from, used as the default save path.
        effect (str | None): Effect to select initially.

    """
    from terminaltexteffects.tui.app import TTEApp  # noqa: PLC0415

    attach_keyboard()
    TTEApp(effect_resource_map, text, input_file, effect).run()
