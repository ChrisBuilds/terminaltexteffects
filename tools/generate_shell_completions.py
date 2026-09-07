"""Generate bundled shell completion scripts from the built-in CLI parser."""

from __future__ import annotations

import argparse
from pathlib import Path

import shtab

from terminaltexteffects import __main__ as tte_main

PROJECT_ROOT = Path(__file__).resolve().parents[1]
COMPLETION_DIR = PROJECT_ROOT / "terminaltexteffects" / "completions"
COMPLETION_PATHS = {
    "bash": COMPLETION_DIR / "tte.bash",
    "zsh": COMPLETION_DIR / "_tte",
}

_BASH_MAPFILE_BLOCK = """  if [[ $pos_only = 0 && "${completing_word}" == -* ]]; then
    # optional argument started: use option strings
    mapfile -t COMPREPLY < <(compgen -W "${current_option_strings[*]}" -- "${completing_word}")
  elif [[ "${previous_word}" == ">" || "${previous_word}" == ">>" ||
          "${previous_word}" =~ ^[12]">" || "${previous_word}" =~ ^[12]">>" ]]; then
    # handle redirection operators
    mapfile -t COMPREPLY < <(compgen -f -- "${completing_word}")
  else
    # use choices & compgen
    [ -n "${current_action_compgen}" ] &&
      mapfile -t COMPREPLY < <("${current_action_compgen}" "${completing_word}")
    mapfile -t -O "${#COMPREPLY[@]}" COMPREPLY < <(
      compgen -W "${current_action_choices[*]}" -- "${completing_word}")
  fi"""

_BASH_32_COMPLETION_BLOCK = """  local completion
  if [[ $pos_only = 0 && "${completing_word}" == -* ]]; then
    # optional argument started: use option strings
    while IFS= read -r completion; do COMPREPLY+=("$completion"); done < <(
      compgen -W "${current_option_strings[*]}" -- "${completing_word}")
  elif [[ "${previous_word}" == ">" || "${previous_word}" == ">>" ||
          "${previous_word}" =~ ^[12]">" || "${previous_word}" =~ ^[12]">>" ]]; then
    # handle redirection operators
    while IFS= read -r completion; do COMPREPLY+=("$completion"); done < <(
      compgen -f -- "${completing_word}")
  else
    # use choices & compgen
    if [ -n "${current_action_compgen}" ]; then
      while IFS= read -r completion; do COMPREPLY+=("$completion"); done < <(
        "${current_action_compgen}" "${completing_word}")
    fi
    while IFS= read -r completion; do COMPREPLY+=("$completion"); done < <(
      compgen -W "${current_action_choices[*]}" -- "${completing_word}")
  fi"""


def _configure_completers(
    parser: argparse.ArgumentParser,
    effect_names: tuple[str, ...],
) -> None:
    """Add generation-only completion metadata to selected parser actions."""
    for action in parser._actions:
        if "--input-file" in action.option_strings:
            action.complete = shtab.FILE  # type: ignore[attr-defined]
        elif "--include-effects" in action.option_strings or "--exclude-effects" in action.option_strings:
            action.choices = effect_names


def _register_aliases(script: str, shell: str) -> str:
    """Register the generated completion function for both CLI entry points."""
    if shell == "bash":
        if _BASH_MAPFILE_BLOCK not in script:
            msg = "shtab's Bash output changed; review the Bash 3.2 compatibility transform"
            raise RuntimeError(msg)
        script = script.replace(_BASH_MAPFILE_BLOCK, _BASH_32_COMPLETION_BLOCK, 1)
        registration = "complete -o filenames -F _shtab_tte tte"
        script = script.replace(
            registration,
            f"{registration}\ncomplete -o filenames -F _shtab_tte terminaltexteffects",
        )
    else:
        script = script.replace("#compdef tte\n", "#compdef tte terminaltexteffects\n", 1)
        script = script.replace(
            "#compdef tte terminaltexteffects\n",
            "#compdef tte terminaltexteffects\n\n"
            "autoload -Uz compinit\n"
            "if ! whence compdef >/dev/null 2>&1; then\n"
            "  compinit\n"
            "fi\n",
            1,
        )
        script = script.replace(
            "compdef _shtab_tte -N tte",
            "compdef _shtab_tte -N tte terminaltexteffects",
        )
    return f"{script.rstrip()}\n"


def build_completion_scripts() -> dict[str, str]:
    """Build completion scripts containing bundled effects only."""
    parser, effect_resource_map = tte_main.build_parser(include_user_effects=False)
    _configure_completers(parser, tuple(effect_resource_map))
    return {
        shell: _register_aliases(shtab.complete(parser, shell=shell), shell)
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
