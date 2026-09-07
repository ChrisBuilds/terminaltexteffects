"""Access bundled shell completion scripts for the terminaltexteffects CLI."""

from __future__ import annotations

from importlib import resources

SUPPORTED_SHELLS = ("bash", "zsh")

_COMPLETION_PACKAGE = "terminaltexteffects.completions"
_COMPLETION_FILES = {
    "bash": "tte.bash",
    "zsh": "_tte",
}


def parse_completion_shell(shell: str) -> str:
    """Validate a requested completion shell while permitting the instruction sentinel."""
    if shell == "" or shell in SUPPORTED_SHELLS:
        return shell
    choices = ", ".join(SUPPORTED_SHELLS)
    msg = f"invalid choice: {shell!r} (choose from {choices})"
    raise ValueError(msg)


def get_completion_instructions() -> str:
    """Return copy-and-paste commands for enabling completion in supported shells."""
    return (
        "Enable completions in the current shell:\n"
        '  Bash: eval "$(tte --print-completion bash)"\n'
        '  Zsh:  eval "$(tte --print-completion zsh)"\n'
    )


def get_completion_script(shell: str) -> str:
    """Return the bundled completion script for `shell`."""
    try:
        filename = _COMPLETION_FILES[shell]
    except KeyError:
        msg = f"Unsupported shell: {shell}"
        raise ValueError(msg) from None
    return resources.read_text(_COMPLETION_PACKAGE, filename, encoding="utf-8")
