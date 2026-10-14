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
