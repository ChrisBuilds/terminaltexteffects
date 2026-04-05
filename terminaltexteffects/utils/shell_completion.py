"""Shell completion generation for the terminaltexteffects CLI."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

SUPPORTED_SHELLS = ("bash", "zsh")


@dataclass(frozen=True)
class CompletionOption:
    """Static completion metadata for a CLI option."""

    option_strings: tuple[str, ...]
    choices: tuple[str, ...] = ()
    takes_value: bool = False
    file_completion: bool = False


def _escape_for_shell(words: Iterable[str]) -> str:
    """Escape static completion words for safe inclusion in a shell script."""
    return " ".join(word.replace("\\", "\\\\").replace('"', '\\"') for word in words)


def _takes_value(action: argparse.Action) -> bool:
    """Return whether an argparse action consumes a value."""
    if isinstance(
        action,
        (
            argparse._HelpAction,
            argparse._StoreTrueAction,
            argparse._StoreFalseAction,
            argparse._VersionAction,
            argparse._CountAction,
            argparse._AppendConstAction,
            argparse._StoreConstAction,
        ),
    ):
        return False
    return action.nargs != 0


def _normalize_choices(action: argparse.Action) -> tuple[str, ...]:
    """Return stringified argparse choices for completion, if any."""
    if action.choices is None:
        return ()
    return tuple(str(choice) for choice in action.choices)


def _build_option_spec(action: argparse.Action) -> CompletionOption | None:
    """Convert an argparse action into static completion metadata."""
    if not action.option_strings:
        return None
    return CompletionOption(
        option_strings=tuple(action.option_strings),
        choices=_normalize_choices(action),
        takes_value=_takes_value(action),
        file_completion="--input-file" in action.option_strings or "-i" in action.option_strings,
    )


def _collect_parser_options(parser: argparse.ArgumentParser) -> tuple[CompletionOption, ...]:
    """Collect static option metadata from a parser."""
    options: list[CompletionOption] = []
    for action in parser._actions:
        option = _build_option_spec(action)
        if option is not None:
            options.append(option)
    return tuple(options)


def _find_subparser_action(parser: argparse.ArgumentParser) -> argparse._SubParsersAction | None:
    """Return the parser's subparser action, if present."""
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return action
    return None


def _format_case_patterns(option: CompletionOption) -> str:
    """Format shell case patterns for the option's aliases."""
    return "|".join(option.option_strings)


def _build_prev_case_block(options: Iterable[CompletionOption], indent: str) -> str:
    """Build a shell case block that completes option values based on the previous word."""
    lines: list[str] = []
    for option in options:
        if option.file_completion:
            lines.extend(
                [
                    f"{indent}{_format_case_patterns(option)})",
                    f'{indent}    COMPREPLY=($(compgen -f -- "$cur"))',
                    f"{indent}    return 0",
                    f"{indent}    ;;",
                ],
            )
        elif option.choices:
            choices = _escape_for_shell(option.choices)
            lines.extend(
                [
                    f"{indent}{_format_case_patterns(option)})",
                    f'{indent}    COMPREPLY=($(compgen -W "{choices}" -- "$cur"))',
                    f"{indent}    return 0",
                    f"{indent}    ;;",
                ],
            )
    return "\n".join(lines)


def _build_bash_completion(parser: argparse.ArgumentParser) -> str:
    """Generate a bash completion script from an argparse parser."""
    global_options = _collect_parser_options(parser)
    subparser_action = _find_subparser_action(parser)
    effect_parsers = subparser_action.choices if subparser_action else {}

    global_words = _escape_for_shell(
        [
            *[option for spec in global_options for option in spec.option_strings],
            *effect_parsers,
        ],
    )
    global_prev_case = _build_prev_case_block(global_options, "        ")

    effect_blocks: list[str] = []
    for effect_name, effect_parser in effect_parsers.items():
        effect_options = _collect_parser_options(effect_parser)
        effect_words = _escape_for_shell([option for spec in effect_options for option in spec.option_strings])
        effect_prev_case = _build_prev_case_block(effect_options, "                ")
        effect_blocks.append(
            "\n".join(
                [
                    f"            {effect_name})",
                    '                case "$prev" in',
                    effect_prev_case or "                    *) ;;",
                    "                esac",
                    f'                COMPREPLY=($(compgen -W "{effect_words}" -- "$cur"))',
                    "                return 0",
                    "                ;;",
                ],
            ),
        )

    effect_case = "\n".join(effect_blocks) if effect_blocks else "            *) ;;"

    return f"""# shellcheck shell=bash
_tte_completion() {{
    local cur prev effect word
    COMPREPLY=()
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    effect=""

    case "$prev" in
{global_prev_case or '        *) ;;'}
    esac

    for word in "${{COMP_WORDS[@]:1}}"; do
        case "$word" in
            {"|".join(effect_parsers)}) effect="$word"; break ;;
        esac
    done

    if [[ -n "$effect" ]]; then
        case "$effect" in
{effect_case}
        esac
    fi

    COMPREPLY=($(compgen -W "{global_words}" -- "$cur"))
    return 0
}}

complete -F _tte_completion tte
complete -F _tte_completion terminaltexteffects
"""


def _build_zsh_completion(parser: argparse.ArgumentParser) -> str:
    """Generate a zsh completion script by enabling bash-style completion."""
    bash_script = _build_bash_completion(parser).rstrip()
    return f"""autoload -Uz compinit bashcompinit
if ! whence compdef >/dev/null 2>&1; then
    compinit
fi
if ! whence complete >/dev/null 2>&1; then
    bashcompinit
fi

{bash_script}
"""


def get_completion_script(shell: str, parser: argparse.ArgumentParser) -> str:
    """Return the shell completion script for the requested shell."""
    if shell == "bash":
        return _build_bash_completion(parser)
    if shell == "zsh":
        return _build_zsh_completion(parser)
    msg = f"Unsupported shell: {shell}"
    raise ValueError(msg)
