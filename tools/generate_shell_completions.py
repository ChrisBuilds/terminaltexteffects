"""Generate bundled shell completion scripts from the built-in CLI parser."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

import shtab

from terminaltexteffects import __main__ as tte_main
from terminaltexteffects.effects import effect_laseretch
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.shell_completion import SUPPORTED_SHELLS

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPLETION_DIR = PROJECT_ROOT / "terminaltexteffects" / "completions"
COMPLETION_PATHS = {
    "bash": COMPLETION_DIR / "tte.bash",
    "zsh": COMPLETION_DIR / "_tte",
    "powershell": COMPLETION_DIR / "tte.ps1",
}

_COMPLETION_CHOICES_BY_TYPE = {
    argutils.CharacterOrderArg.type_parser: argutils.CharacterOrderArg.COMPLETION_CHOICES,
    argutils.CharacterGroupArg.type_parser: argutils.CharacterGroupArg.COMPLETION_CHOICES,
    argutils.CharacterSortArg.type_parser: argutils.CharacterSortArg.COMPLETION_CHOICES,
    argutils.CharacterGroupOrSortArg.type_parser: argutils.CharacterGroupOrSortArg.COMPLETION_CHOICES,
    argutils.ColorSortArg.type_parser: argutils.ColorSortArg.COMPLETION_CHOICES,
    argutils.GradientDirection.type_parser: argutils.GradientDirection.COMPLETION_CHOICES,
    argutils.Ease.type_parser: argutils.Ease.COMPLETION_CHOICES,
    effect_laseretch._etch_pattern_type_parser: ("algorithm", *argutils.CharacterOrderArg.COMPLETION_CHOICES),
}


def _configure_completers(
    parser: argparse.ArgumentParser,
    effect_names: tuple[str, ...],
) -> None:
    """Add generation-only completion metadata to selected parser actions."""
    for action in parser._actions:
        if "--input-file" in action.option_strings:
            action.complete = shtab.FILE  # type: ignore[attr-defined]
        elif "--print-completion" in action.option_strings:
            action.choices = SUPPORTED_SHELLS
        elif "--include-effects" in action.option_strings or "--exclude-effects" in action.option_strings:
            action.choices = effect_names
        elif action.choices is None and action.type in _COMPLETION_CHOICES_BY_TYPE:
            action.choices = _COMPLETION_CHOICES_BY_TYPE[action.type]
        if isinstance(action, argparse._SubParsersAction):
            subparsers = cast("dict[str, argparse.ArgumentParser]", action.choices)
            for subparser in subparsers.values():
                _configure_completers(subparser, effect_names)


def _register_aliases(script: str, shell: str) -> str:
    """Register the generated completion function for both CLI entry points."""
    if shell == "bash":
        # shtab 1.12 uses read loops compatible with Bash 3.2; no mapfile transform is needed.
        registration = "complete -F _shtab_tte tte"
        if registration not in script:
            msg = "shtab's Bash registration changed; review CLI alias registration"
            raise RuntimeError(msg)
        script = script.replace(
            registration,
            "complete -o filenames -F _shtab_tte tte\ncomplete -o filenames -F _shtab_tte terminaltexteffects",
            1,
        )
    else:
        script = script.replace("#compdef tte\n", "#compdef tte terminaltexteffects\n", 1)
        script = script.replace(
            "#compdef tte terminaltexteffects\n",
            "#compdef tte terminaltexteffects\n\n"
            "autoload -Uz compinit\n"
            "if ! whence compdef >/dev/null 2>&1; then\n"
            "  compinit -i\n"
            "fi\n",
            1,
        )
        script = script.replace(
            "compdef _shtab_tte -N tte",
            "compdef _shtab_tte -N tte terminaltexteffects",
        )
    return f"{script.rstrip()}\n"


def parser_metadata(parser: argparse.ArgumentParser) -> dict[str, object]:
    """Describe options, arity, and subcommands without serializing executable validators."""
    options: dict[str, object] = {}
    effects: dict[str, object] = {}
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, child in cast("dict[str, argparse.ArgumentParser]", action.choices).items():
                effects[name] = parser_metadata(child)["root"]
            continue
        if not action.option_strings or action.help == argparse.SUPPRESS:
            continue
        nargs = action.nargs
        if nargs is None:
            minimum, maximum = 1, 1
        elif isinstance(nargs, int):
            minimum, maximum = nargs, nargs
        elif nargs == "?":
            minimum, maximum = 0, 1
        elif nargs in ("+", "*"):
            minimum, maximum = int(nargs == "+"), -1
        else:
            msg = f"Unsupported PowerShell completion arity: {nargs!r}"
            raise ValueError(msg)
        info = {
            "min": minimum,
            "max": maximum,
            "choices": [str(value) for value in action.choices] if action.choices is not None else [],
            "file": "--input-file" in action.option_strings,
            "help": action.help or action.dest,
        }
        for name in action.option_strings:
            options[name] = info
    return {"root": {"options": options}, "effects": effects}


def build_powershell_script(parser: argparse.ArgumentParser) -> str:
    """Embed parser data into a PowerShell 7 template using a literal JSON here-string."""
    template = Path(__file__).with_name("completions") / "powershell.ps1"
    metadata = json.dumps(parser_metadata(parser), ensure_ascii=True, indent=2)
    return template.read_text(encoding="utf-8").replace("__TTE_METADATA__", metadata)


def build_completion_scripts() -> dict[str, str]:
    """Build completion scripts containing bundled effects only."""
    parser, effect_resource_map = tte_main.build_parser(include_user_effects=False)
    _configure_completers(parser, tuple(effect_resource_map))
    return {
        shell: (
            build_powershell_script(parser)
            if shell == "powershell"
            else _register_aliases(shtab.complete(parser, shell=shell), shell)
        )
        for shell in COMPLETION_PATHS
    }


def write_completion_scripts(*, check: bool = False) -> bool:
    """Write generated scripts, or return whether committed scripts are current."""
    scripts = build_completion_scripts()
    if check:
        return all(
            path.exists() and path.read_text(encoding="utf-8") == scripts[shell]
            for shell, path in COMPLETION_PATHS.items()
        )
    COMPLETION_DIR.mkdir(parents=True, exist_ok=True)
    for shell, path in COMPLETION_PATHS.items():
        path.write_text(scripts[shell], encoding="utf-8")
    return True


def main() -> None:
    """Generate completion resources or verify that they are current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if bundled scripts differ from generated output")
    args = parser.parse_args()
    if not write_completion_scripts(check=args.check):
        parser.error("bundled completion scripts are out of date; run this command without --check")


if __name__ == "__main__":
    main()
