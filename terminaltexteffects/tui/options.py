"""Describe effect and terminal configuration options for the TUI option editor.

Every option is derived from the `ArgSpec` default of a `BaseConfig` dataclass field, so built-in, user, and
development effects get an editor without effect-specific code. Text entered in the editor uses the command-line
spelling of each option and is validated with `ArgSpec.normalize`, the same contract used by the CLI and library.

This module does not import Textual.
"""

from __future__ import annotations

import argparse
import shlex
import typing
from dataclasses import dataclass, fields

from terminaltexteffects.utils import argutils

if typing.TYPE_CHECKING:
    from terminaltexteffects.engine.base_config import BaseConfig

OptionKind = typing.Literal["bool", "choice", "text"]

_CHOICES_BY_TYPE: dict[typing.Any, tuple[str, ...]] = {
    argutils.CharacterOrderArg.type_parser: argutils.CharacterOrderArg.COMPLETION_CHOICES,
    argutils.CharacterGroupArg.type_parser: argutils.CharacterGroupArg.COMPLETION_CHOICES,
    argutils.CharacterSortArg.type_parser: argutils.CharacterSortArg.COMPLETION_CHOICES,
    argutils.CharacterGroupOrSortArg.type_parser: argutils.CharacterGroupOrSortArg.COMPLETION_CHOICES,
    argutils.ColorSortArg.type_parser: argutils.ColorSortArg.COMPLETION_CHOICES,
    argutils.GradientDirection.type_parser: argutils.GradientDirection.COMPLETION_CHOICES,
    argutils.Ease.type_parser: argutils.Ease.COMPLETION_CHOICES,
}

TUI_TERMINAL_OPTIONS = (
    "canvas_width",
    "canvas_height",
    "anchor_canvas",
    "anchor_text",
    "wrap_text",
    "frame_rate",
    "existing_color_handling",
    "terminal_background_color",
    "no_color",
    "xterm_colors",
    "tab_width",
)
"""`TerminalConfig` fields shown on the TUI's canvas tab, in display order."""

TUI_TERMINAL_DEFAULTS: dict[str, typing.Any] = {
    "canvas_width": 0,
    "canvas_height": 0,
    "anchor_canvas": "nw",
    "anchor_text": "nw",
}
"""TUI defaults that differ from the CLI, so the canvas fills the text area and text lands where it was typed."""


class _Format(typing.NamedTuple):
    """How to write one value of an option type, for tooltips."""

    one: str
    many: str
    example: str
    examples: str


_FORMATS: dict[typing.Any, _Format] = {
    argutils.PositiveInt.type_parser: _Format("a whole number above 0", "whole numbers above 0", "4", "2 6 10"),
    argutils.NonNegativeInt.type_parser: _Format("a whole number, 0 or more", "whole numbers, 0 or more", "0", "0 3 8"),
    argutils.PositiveIntRange.type_parser: _Format(
        "a range of whole numbers above 0, written low-high",
        "ranges of whole numbers, written low-high",
        "2-8",
        "1-4 6-9",
    ),
    argutils.PositiveFloat.type_parser: _Format("a number above 0", "numbers above 0", "0.5", "0.25 1 2.5"),
    argutils.NonNegativeFloat.type_parser: _Format("a number, 0 or more", "numbers, 0 or more", "0", "0 0.5 2"),
    argutils.PositiveFloatRange.type_parser: _Format(
        "a range of numbers above 0, written low-high", "ranges of numbers, written low-high", "0.25-1.5", "0.1-0.5 1-2"
    ),
    argutils.NonNegativeRatio.type_parser: _Format("a number from 0 to 1", "numbers from 0 to 1", "0.5", "0 0.5 1"),
    argutils.PositiveRatio.type_parser: _Format(
        "a number above 0, up to 1", "numbers above 0, up to 1", "0.25", "0.1 0.5 1"
    ),
    argutils.EasingStep.type_parser: _Format("a number above 0, up to 1", "numbers above 0, up to 1", "0.1", "0.1 0.5"),
    argutils.ColorArg.type_parser: _Format(
        "a color: an RGB hex value from 000000 to ffffff, or an XTerm color number from 0 to 255",
        "colors: RGB hex values from 000000 to ffffff, or XTerm color numbers from 0 to 255",
        "ff8800",
        "ff0000 00ff00 208",
    ),
    argutils.Symbol.type_parser: _Format("one character", "single characters (quote a space as ' ')", "*", "* + ."),
    argutils.CanvasDimension.type_parser: _Format(
        "a whole number of cells: -1 follows the text size, and 0 fills the area", "", "40", ""
    ),
    argutils.TerminalDimension.type_parser: _Format("a whole number of cells: 0 uses the terminal size", "", "80", ""),
    int: _Format("a whole number", "whole numbers", "3", "1 2 3"),
    float: _Format("a number", "numbers", "0.5", "0.5 1 1.5"),
}
"""Value formats by `ArgSpec` type parser."""


@dataclass(frozen=True)
class OptionField:
    """One editable configuration option.

    Attributes:
        name (str): Config dataclass field name.
        spec (argutils.ArgSpec): The field's argument specification.
        default (typing.Any): Canonical value shown when the editor is reset.

    """

    name: str
    spec: argutils.ArgSpec
    default: typing.Any

    @property
    def flag(self) -> str:
        """Return the command-line flag, such as `--typing-speed`."""
        return self.spec.name

    @property
    def help(self) -> str:
        """Return the option's help text, or an empty string."""
        return "" if self.spec.help is argutils._MISSING else self.spec.help

    @property
    def is_multi(self) -> bool:
        """Return whether the option takes a space-separated list of values."""
        return self.spec.action is argutils.TupleAction

    @property
    def kind(self) -> OptionKind:
        """Return the editor kind: a checkbox, a fixed-choice select, or free text."""
        if self.spec.action == "store_true":
            return "bool"
        if not self.is_multi and self.choices:
            return "choice"
        return "text"

    @property
    def choices(self) -> tuple[str, ...]:
        """Return the fixed command-line choices, or an empty tuple when the value is free text."""
        if self.spec.choices is not argutils._MISSING:
            return tuple(str(choice) for choice in self.spec.choices)
        return _CHOICES_BY_TYPE.get(self.spec.type, ())

    @property
    def is_color(self) -> bool:
        """Return whether the option's values are colors."""
        return self.spec.type is argutils.ColorArg.type_parser

    def format_hint(self) -> str:
        """Return how to write the option's value, with an example, or an empty string for checkboxes and lists.

        Types the TUI does not know, such as those of community effects, are described by their `ArgSpec` metavar,
        with the default value as the example.
        """
        if self.kind != "text":
            return ""
        known = _FORMATS.get(self.spec.type)
        if known is not None and (known.many or not self.is_multi):
            if self.is_multi:
                return f"Format: space-separated {known.many}.\nExample: {known.examples}"
            return f"Format: {known.one}.\nExample: {known.example}"
        metavar = "" if self.spec.metavar is argutils._MISSING else self.spec.metavar
        if isinstance(metavar, (tuple, list)):
            metavar = " ".join(str(item) for item in metavar)
        metavar = str(metavar).strip()
        if isinstance(self.default, tuple) and len(self.default) == 2 and not self.is_multi:
            numbers = "whole numbers" if all(isinstance(item, int) for item in self.default) else "numbers"
            description = f"Format: a range of {numbers}, written low-high."
        elif not metavar:
            description = ""
        elif self.is_multi:
            description = f"Format: space-separated values, each {metavar.strip('()')}."
        elif " " in metavar and "(" not in metavar:
            description = f"Format: one of {', '.join(metavar.split())}."
        else:
            description = f"Format: {metavar.strip('()')}."
        example = self.format(self.default)
        if not example:
            return description
        return f"{description}\nExample: {example}".strip()

    def format(self, value: typing.Any) -> str:
        """Return `value` as editor text using the command-line spelling.

        List values are joined with shell quoting so values such as a space symbol survive a round trip.
        """
        if self.kind == "bool":
            return "true" if value else "false"
        if self.is_multi:
            items = value if isinstance(value, (tuple, list)) else (value,)
            return " ".join(_quote_if_needed(self._format_item(item)) for item in items)
        return self._format_item(value)

    def _format_item(self, value: typing.Any) -> str:
        """Return one value's command-line spelling.

        A two-number tuple on a single-value option is a range, including ranges with effect-specific parsers.
        """
        if not self.is_multi and isinstance(value, tuple) and len(value) == 2:
            return argutils.format_cli_range(value)
        return argutils.format_cli_default(value, self.spec.type)

    def parse(self, text: str) -> typing.Any:
        """Return the canonical value for editor `text`.

        Raises:
            ValueError: If `text` is not a valid value for the option.

        """
        value: typing.Any = text
        if self.is_multi:
            try:
                value = shlex.split(text)
            except ValueError as error:
                msg = f"invalid value: {error}."
                raise ValueError(msg) from error
        try:
            return self.spec.normalize(value)
        except (argparse.ArgumentTypeError, TypeError, ValueError) as error:
            raise ValueError(str(error)) from error

    def command_tokens(self, value: typing.Any) -> list[str]:
        """Return the command-line tokens that set this option to `value`."""
        if self.kind == "bool":
            return [self.flag] if value else []
        items = value if self.is_multi and isinstance(value, (tuple, list)) else (value,)
        return [self.flag, *(self._format_item(item) for item in items)]


def _quote_if_needed(token: str) -> str:
    """Quote a list item for `shlex.split` only when it contains whitespace, quotes, or backslashes, or is empty."""
    if token and not any(character.isspace() or character in "'\"\\" for character in token):
        return token
    return shlex.quote(token)


def option_fields(
    config_class: type[BaseConfig],
    include: typing.Iterable[str] | None = None,
    defaults: dict[str, typing.Any] | None = None,
) -> list[OptionField]:
    """Return the editable options of `config_class`.

    Args:
        config_class (type[BaseConfig]): Effect or terminal config class.
        include (Iterable[str] | None): Field names to include, in display order. All `ArgSpec` fields in declaration
            order when omitted.
        defaults (dict[str, Any] | None): Defaults that replace the `ArgSpec` defaults for named fields.

    Returns:
        list[OptionField]: Option descriptions.

    """
    specs = {field.name: field.default for field in fields(config_class) if isinstance(field.default, argutils.ArgSpec)}
    names = list(specs) if include is None else [name for name in include if name in specs]
    defaults = defaults or {}
    result = []
    for name in names:
        spec = typing.cast("argutils.ArgSpec", specs[name])
        result.append(OptionField(name, spec, spec.normalize(defaults.get(name, spec.default))))
    return result


def build_config(config_class: type[BaseConfig], values: dict[str, typing.Any]) -> BaseConfig:
    """Return a `config_class` instance with `values` applied over its defaults."""
    config = config_class._build_config()
    for name, value in values.items():
        setattr(config, name, value)
    return config


def command_line(
    effect_name: str,
    effect_options: list[tuple[OptionField, typing.Any]],
    terminal_options: list[tuple[OptionField, typing.Any]],
    input_file: str | None = None,
) -> str:
    """Return a shell command that plays the configured effect with the CLI.

    Options equal to their `ArgSpec` (CLI) default are omitted, so TUI-specific terminal defaults such as a
    whole-area canvas appear explicitly.

    Args:
        effect_name (str): Effect command name.
        effect_options (list[tuple[OptionField, Any]]): Effect options and their current values.
        terminal_options (list[tuple[OptionField, Any]]): Terminal options and their current values.
        input_file (str | None): File to read the text from, passed with `--input-file`.

    Returns:
        str: The quoted command line.

    """
    tokens = ["tte"]
    if input_file:
        tokens += ["--input-file", input_file]
    for option, value in terminal_options:
        if value != option.spec.normalize(option.spec.default):
            tokens += option.command_tokens(value)
    tokens.append(effect_name)
    for option, value in effect_options:
        if value != option.spec.normalize(option.spec.default):
            tokens += option.command_tokens(value)
    return shlex.join(tokens)


@dataclass
class ParsedCommand:
    """Settings read from a `tte` command line.

    Attributes:
        effect (str): Effect command name.
        effect_values (dict[str, Any]): Effect option values given in the command, by field name.
        terminal_values (dict[str, Any]): Terminal option values given in the command, by field name.
        input_file (str | None): File given with `--input-file`.
        problems (list[str]): Flags or values that could not be applied.

    """

    effect: str
    effect_values: dict[str, typing.Any]
    terminal_values: dict[str, typing.Any]
    input_file: str | None
    problems: list[str]


def parse_command(
    command: str,
    effect_fields: typing.Mapping[str, typing.Callable[[], list[OptionField]]],
    terminal_fields: list[OptionField],
) -> ParsedCommand:
    """Read the effect and options from a `tte` command line, such as one shown by the command dialog.

    Flags before the effect name are terminal options, and flags after it are effect options. Each flag's values run
    until the next flag. Unknown flags and invalid values are reported in `problems` instead of failing the whole
    command.

    Args:
        command (str): The command line. A leading `tte` is optional.
        effect_fields (Mapping[str, Callable[[], list[OptionField]]]): Effect names mapped to functions that return
            their option fields.
        terminal_fields (list[OptionField]): Terminal option fields that can be set.

    Returns:
        ParsedCommand: The settings found in the command.

    Raises:
        ValueError: If the command cannot be split or names no known effect.

    """
    try:
        tokens = shlex.split(command)
    except ValueError as error:
        msg = f"cannot read the command: {error}."
        raise ValueError(msg) from error
    if tokens and tokens[0] in ("tte", "terminaltexteffects"):
        tokens = tokens[1:]
    effect_index = next((index for index, token in enumerate(tokens) if token in effect_fields), None)
    if effect_index is None:
        msg = "the command names no known effect."
        raise ValueError(msg)
    effect = tokens[effect_index]
    problems: list[str] = []
    input_file: str | None = None
    terminal_tokens = tokens[:effect_index]
    for index, token in enumerate(terminal_tokens):
        if token in ("-i", "--input-file") and index + 1 < len(terminal_tokens):
            input_file = terminal_tokens[index + 1]
            terminal_tokens = terminal_tokens[:index] + terminal_tokens[index + 2 :]
            break
    terminal_values = _parse_flags(terminal_tokens, terminal_fields, problems)
    effect_values = _parse_flags(tokens[effect_index + 1 :], effect_fields[effect](), problems)
    return ParsedCommand(effect, effect_values, terminal_values, input_file, problems)


def _parse_flags(tokens: list[str], fields_: list[OptionField], problems: list[str]) -> dict[str, typing.Any]:
    """Return the values of the flags in `tokens`, adding unknown flags and invalid values to `problems`."""
    by_flag = {option.flag: option for option in fields_}
    values: dict[str, typing.Any] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if not token.startswith("--"):
            problems.append(f"unexpected value '{token}'")
            continue
        flag, _, inline = token.partition("=")
        arguments = [inline] if inline else []
        while index < len(tokens) and not tokens[index].startswith("--"):
            arguments.append(tokens[index])
            index += 1
        option = by_flag.get(flag)
        if option is None:
            problems.append(f"{flag} is not available here")
            continue
        try:
            if option.kind == "bool":
                values[option.name] = True
                if arguments:
                    problems.append(f"{flag} takes no value")
            else:
                text = " ".join(_quote_if_needed(argument) for argument in arguments) if option.is_multi else ""
                values[option.name] = option.parse(text if option.is_multi else " ".join(arguments))
        except ValueError as error:
            problems.append(f"{flag}: {error}")
    return values
