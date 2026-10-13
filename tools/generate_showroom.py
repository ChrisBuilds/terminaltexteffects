"""Regenerate the command-line argument blocks in the effects showroom from the built-in CLI parser."""

from __future__ import annotations

import argparse
import re
import sys
import textwrap
from pathlib import Path
from typing import cast

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.utils import argutils

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SHOWROOM_PATH = PROJECT_ROOT / "docs" / "showroom.md"
HELP_WIDTH = 116
BLOCK_INDENT = "    "

_SECTION = re.compile(r"^## (?P<title>.+)$", re.MULTILINE)
_ARGUMENT_BLOCK = re.compile(
    r'(?P<head>^\?\?\? example "(?P<title>[^"]+) Command Line Arguments"\n\n    ```\n)(?P<body>.*?)(?P<tail>^    ```$)',
    re.MULTILINE | re.DOTALL,
)


def effect_parsers() -> dict[str, argparse.ArgumentParser]:
    """Return built-in effect subparsers by command name, excluding plugins and development effects."""
    parser, _ = build_parser(include_user_effects=False)
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            return dict(cast("dict[str, argparse.ArgumentParser]", action.choices))
    message = "The CLI parser has no effect subcommands"
    raise RuntimeError(message)


def render_arguments(parser: argparse.ArgumentParser) -> str:
    """Render effect options and epilog without depending on terminal width or argparse layout changes."""
    formatter = argutils.CustomFormatter(prog=parser.prog)
    lines: list[str] = []
    for action in parser._actions:
        if isinstance(action, argparse._HelpAction):
            continue
        lines.append(formatter._format_action_invocation(action))
        help_text = " ".join(formatter._expand_help(action).split())
        lines.extend(textwrap.wrap(help_text, HELP_WIDTH, initial_indent="    ", subsequent_indent="    "))
    if parser.epilog:
        lines.extend(["", *render_epilog(parser.epilog)])
    return "".join(f"{BLOCK_INDENT}{line}\n" if line else "\n" for line in lines)


def render_epilog(epilog: str) -> list[str]:
    """Dedent shared epilog notes, such as easing help, and separate them from the trailing example line."""
    lines = [line.rstrip() for line in epilog.strip("\n").splitlines()]
    notes = [line for line in lines if line.strip() and not line.startswith("Example:")]
    indent = min((len(line) - len(line.lstrip()) for line in notes), default=0)
    rendered: list[str] = []
    for line in lines:
        if line.startswith("Example:") and rendered and rendered[-1]:
            rendered.append("")
        rendered.append(line if line.startswith("Example:") else line[indent:])
    return rendered


def render_showroom(source: str, parsers: dict[str, argparse.ArgumentParser]) -> str:
    """Replace each effect's argument block and verify the showroom covers exactly the built-in effects."""
    sections = {match.group("title").strip().lower() for match in _SECTION.finditer(source)}
    if sections != set(parsers):
        missing = ", ".join(sorted(set(parsers) - sections)) or "none"
        extra = ", ".join(sorted(sections - set(parsers))) or "none"
        message = f"Showroom sections do not match built-in effects (missing: {missing}; unknown: {extra})"
        raise ValueError(message)

    rendered: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        command = match.group("title").strip().lower()
        if command not in parsers or command in rendered:
            message = f"Unexpected or duplicate argument block for {match.group('title')!r}"
            raise ValueError(message)
        rendered.add(command)
        return match.group("head") + render_arguments(parsers[command]) + match.group("tail")

    updated = _ARGUMENT_BLOCK.sub(replace, source)
    if rendered != set(parsers):
        missing = ", ".join(sorted(set(parsers) - rendered))
        message = f"Showroom is missing argument blocks for: {missing}"
        raise ValueError(message)
    return updated


def main(argv: list[str] | None = None) -> int:
    """Write the regenerated showroom, or with `--check` report whether it is current."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the showroom is out of date.")
    args = parser.parse_args(argv)

    source = SHOWROOM_PATH.read_text(encoding="utf-8")
    updated = render_showroom(source, effect_parsers())
    if args.check:
        if updated != source:
            print(
                f"{SHOWROOM_PATH.relative_to(PROJECT_ROOT)} is out of date; run tools/generate_showroom.py",
                file=sys.stderr,
            )
            return 1
        return 0
    if updated != source:
        SHOWROOM_PATH.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
