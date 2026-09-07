"""Access bundled shell completion scripts for the terminaltexteffects CLI."""

from __future__ import annotations

from importlib import resources

SUPPORTED_SHELLS = ("bash", "zsh")

_COMPLETION_PACKAGE = "terminaltexteffects.completions"
_COMPLETION_FILES = {
    "bash": "tte.bash",
    "zsh": "_tte",
}


def get_completion_script(shell: str) -> str:
    """Return the bundled completion script for `shell`."""
    try:
        filename = _COMPLETION_FILES[shell]
    except KeyError:
        msg = f"Unsupported shell: {shell}"
        raise ValueError(msg) from None
    return resources.read_text(_COMPLETION_PACKAGE, filename, encoding="utf-8")
