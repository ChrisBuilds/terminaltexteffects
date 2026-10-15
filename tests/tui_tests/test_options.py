"""Tests for deriving TUI option editors from effect configuration specs."""

from __future__ import annotations

import functools
import shlex
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.__main__ import build_parser
from terminaltexteffects.engine.terminal import TerminalConfig
from terminaltexteffects.tui import options
from terminaltexteffects.utils import argutils
from terminaltexteffects.utils.graphics import Color, Gradient

if TYPE_CHECKING:
    from terminaltexteffects.engine.base_config import BaseConfig

_, _EFFECTS = build_parser(include_user_effects=False)
_CONFIGS: list[tuple[str, type[BaseConfig]]] = [(name, config) for name, (_, config) in sorted(_EFFECTS.items())]
_CONFIGS.append(("terminal", TerminalConfig))


@pytest.mark.parametrize(("name", "config_class"), _CONFIGS, ids=[name for name, _ in _CONFIGS])
def test_every_option_default_round_trips_through_its_editor_text(name: str, config_class: type[BaseConfig]) -> None:
    """Every built-in option's default should format as text that parses back to the same value."""
    fields = options.option_fields(config_class)
    assert fields, name
    for option in fields:
        if option.kind == "bool":
            assert isinstance(option.default, bool)
            continue
        text = option.format(option.default)
        assert option.parse(text) == option.default, option.flag
        if option.kind == "choice":
            assert text in option.choices, option.flag
    options.build_config(config_class, {option.name: option.default for option in fields})


def test_option_kinds_follow_arg_specs() -> None:
    """Booleans, fixed choices, and free text should map to their editor kinds."""
    fields = {option.name: option for option in options.option_fields(TerminalConfig)}
    assert fields["wrap_text"].kind == "bool"
    assert fields["anchor_canvas"].kind == "choice"
    assert fields["anchor_canvas"].choices == ("sw", "s", "se", "e", "ne", "n", "nw", "w", "c")
    assert fields["frame_rate"].kind == "text"
    assert fields["terminal_background_color"].is_color

    decrypt = {option.name: option for option in options.option_fields(_EFFECTS["decrypt"][1])}
    assert decrypt["final_gradient_direction"].kind == "choice"
    assert decrypt["ciphertext_colors"].is_multi
    assert decrypt["ciphertext_colors"].kind == "text"


def test_parse_uses_command_line_syntax_and_reports_errors() -> None:
    """Editor text should use the CLI spelling and raise `ValueError` with the parser message."""
    decrypt = {option.name: option for option in options.option_fields(_EFFECTS["decrypt"][1])}
    assert decrypt["ciphertext_colors"].parse("ff0000 00ff00") == (Color("ff0000"), Color("00ff00"))
    assert decrypt["final_gradient_direction"].parse("radial") is Gradient.Direction.RADIAL
    with pytest.raises(ValueError, match="invalid"):
        decrypt["typing_speed"].parse("0")
    with pytest.raises(ValueError, match="at least one"):
        decrypt["ciphertext_colors"].parse("")
    with pytest.raises(ValueError, match="invalid value"):
        decrypt["ciphertext_colors"].parse("'unterminated")


def test_symbol_lists_quote_spaces() -> None:
    """A space symbol in a list should survive formatting and parsing."""
    spec = argutils.ArgSpec(
        name="--symbols",
        type=argutils.Symbol.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=("a", " ", "b"),
    )
    option = options.OptionField("symbols", spec, spec.normalize(spec.default))
    text = option.format(option.default)
    assert shlex.split(text) == ["a", " ", "b"]
    assert option.parse(text) == ("a", " ", "b")


def test_effect_specific_range_parsers_format_as_ranges() -> None:
    """A range with an effect-specific parser should use the hyphenated CLI spelling."""
    overflow = {option.name: option for option in options.option_fields(_EFFECTS["overflow"][1])}
    assert overflow["overflow_cycles_range"].format((2, 4)) == "2-4"


def test_tui_terminal_defaults_fill_the_text_area() -> None:
    """The canvas tab should default to a whole-area canvas with text anchored where it was typed."""
    fields = options.option_fields(TerminalConfig, options.TUI_TERMINAL_OPTIONS, options.TUI_TERMINAL_DEFAULTS)
    assert [option.name for option in fields] == list(options.TUI_TERMINAL_OPTIONS)
    defaults = {option.name: option.default for option in fields}
    assert defaults["canvas_width"] == defaults["canvas_height"] == 0
    assert defaults["anchor_canvas"] == defaults["anchor_text"] == "nw"


def test_command_line_includes_only_values_that_differ_from_cli_defaults() -> None:
    """The exported command should omit CLI defaults and quote values for the shell."""
    effect_fields = options.option_fields(_EFFECTS["decrypt"][1])
    terminal_fields = options.option_fields(
        TerminalConfig,
        options.TUI_TERMINAL_OPTIONS,
        options.TUI_TERMINAL_DEFAULTS,
    )
    effect_values = [
        (option, (Color("ff0000"), Color(208)) if option.name == "ciphertext_colors" else option.default)
        for option in effect_fields
    ]
    terminal_values = [(option, True if option.name == "wrap_text" else option.default) for option in terminal_fields]

    command = options.command_line("decrypt", effect_values, terminal_values, "my text.txt")

    assert shlex.split(command) == [
        "tte",
        "--input-file",
        "my text.txt",
        "--canvas-width",
        "0",
        "--canvas-height",
        "0",
        "--anchor-canvas",
        "nw",
        "--anchor-text",
        "nw",
        "--wrap-text",
        "decrypt",
        "--ciphertext-colors",
        "ff0000",
        "208",
    ]
    args = build_parser(include_user_effects=False)[0].parse_args(shlex.split(command)[1:])
    assert args.ciphertext_colors == (Color("ff0000"), Color(208))
    assert args.wrap_text is True


def test_list_items_are_quoted_only_when_needed() -> None:
    """Unicode symbols should read naturally while shell-special items stay quoted."""
    spec = argutils.ArgSpec(
        name="--symbols",
        type=argutils.Symbol.type_parser,
        nargs="+",
        action=argutils.TupleAction,
        default=("▂", "'", "\\"),
    )
    option = options.OptionField("symbols", spec, spec.normalize(spec.default))
    text = option.format(option.default)
    assert text.startswith("▂ ")
    assert option.parse(text) == ("▂", "'", "\\")


def _command_fields() -> tuple[dict[str, functools.partial[list[options.OptionField]]], list[options.OptionField]]:
    effect_fields = {
        name: functools.partial(options.option_fields, config_class) for name, (_, config_class) in _EFFECTS.items()
    }
    terminal_fields = options.option_fields(TerminalConfig, options.TUI_TERMINAL_OPTIONS, options.TUI_TERMINAL_DEFAULTS)
    return effect_fields, terminal_fields


def test_parse_command_reads_back_an_exported_command() -> None:
    """A command from `command_line` should parse back to the values it was built from."""
    effect_fields, terminal_fields = _command_fields()
    decrypt_fields = effect_fields["decrypt"]()
    colors = (Color("ff0000"), Color(208))
    effect_values = [
        (option, colors if option.name == "ciphertext_colors" else option.default) for option in decrypt_fields
    ]
    terminal_values = [(option, 30 if option.name == "frame_rate" else option.default) for option in terminal_fields]
    command = options.command_line("decrypt", effect_values, terminal_values, "my text.txt")

    parsed = options.parse_command(command, effect_fields, terminal_fields)

    assert parsed.effect == "decrypt"
    assert parsed.effect_values == {"ciphertext_colors": colors}
    assert parsed.terminal_values == {
        "canvas_width": 0,
        "canvas_height": 0,
        "anchor_canvas": "nw",
        "anchor_text": "nw",
        "frame_rate": 30,
    }
    assert parsed.input_file == "my text.txt"
    assert parsed.problems == []


def test_parse_command_reports_flags_it_cannot_apply() -> None:
    """Unknown flags and invalid values should be reported without failing the rest of the command."""
    effect_fields, terminal_fields = _command_fields()

    parsed = options.parse_command(
        "--reuse-canvas wipe stray --wipe-delay=x --reverse-wipe-direction --wipe-ease IN_OUT_CIRC",
        effect_fields,
        terminal_fields,
    )

    assert parsed.effect == "wipe"
    assert parsed.effect_values["reverse_wipe_direction"] is True
    assert "wipe_ease" in parsed.effect_values
    assert parsed.terminal_values == {}
    assert len(parsed.problems) == 3
    assert parsed.problems[:2] == ["--reuse-canvas is not available here", "unexpected value 'stray'"]
    assert parsed.problems[2].startswith("--wipe-delay:")
    with pytest.raises(ValueError, match="no known effect"):
        options.parse_command("tte --frame-rate 30", effect_fields, terminal_fields)
    with pytest.raises(ValueError, match="cannot read"):
        options.parse_command("tte wipe --final-gradient-stops 'ff0000", effect_fields, terminal_fields)


def test_format_hints_describe_the_value_and_give_an_example() -> None:
    """Text options should explain how to write their value, with an example, and others should have no hint."""
    by_name = {
        f"{name}.{option.name}": option
        for name, (_, config_class) in _EFFECTS.items()
        for option in options.option_fields(config_class)
    }
    assert by_name["beams.beam_row_speed_range"].format_hint() == (
        "Format: a range of whole numbers above 0, written low-high.\nExample: 2-8"
    )
    assert by_name["beams.beam_row_symbols"].format_hint().startswith("Format: space-separated single characters")
    assert "Example: ff0000 00ff00 208" in by_name["beams.final_gradient_stops"].format_hint()
    assert by_name["overflow.overflow_cycles_range"].format_hint() == (
        "Format: a range of whole numbers, written low-high.\nExample: 2-4"
    )
    assert by_name["laseretch.etch_pattern"].format_hint().startswith("Format: one of algorithm, column_left_to_right,")
    assert by_name["wipe.reverse_wipe_direction"].format_hint() == ""
    assert by_name["wipe.wipe_ease"].format_hint() == ""
    for key, option in by_name.items():
        if option.kind == "text":
            assert "Format: " in option.format_hint(), key
            assert "\nExample: " in option.format_hint(), key
