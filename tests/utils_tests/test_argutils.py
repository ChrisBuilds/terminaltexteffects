"""Test argument parsing and canonical values."""

from __future__ import annotations

from argparse import ArgumentTypeError
from typing import TYPE_CHECKING

import pytest

from terminaltexteffects.utils import argutils, easing
from terminaltexteffects.utils.graphics import Color, Gradient

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (argutils.CharacterGroup.ROW_TOP_TO_BOTTOM, "row_top_to_bottom"),
        (Gradient.Direction.VERTICAL, "vertical"),
        (Color("aabbcc"), "aabbcc"),
        ((Color("aabbcc"), Color(42)), "aabbcc 42"),
        (easing.in_out_sine, "in_out_sine"),
    ],
)
def test_format_cli_default_uses_cli_spellings(value: object, expected: str) -> None:
    """Canonical built-in values should render as valid command-line values."""
    assert argutils.format_cli_default(value) == expected


def test_format_cli_range_uses_hyphenated_cli_syntax() -> None:
    """Range defaults should use the format accepted by range parsers."""
    assert argutils.format_cli_range((1, 10)) == "1-10"
    assert argutils.format_cli_range((0.1, 0.5)) == "0.1-0.5"
    assert argutils.format_cli_default((1, 10), argutils.PositiveIntRange.type_parser) == "1-10"


def test_positive_int_valid_int() -> None:
    """Verify `PositiveInt` accepts valid CLI values."""
    assert argutils.PositiveInt.type_parser("1") == 1


@pytest.mark.parametrize("arg", ["-1", "0", "1.1", "a"])
def test_positive_int_invalid_int(arg: str) -> None:
    """Verify `PositiveInt` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveInt.type_parser(arg)


def test_non_negative_int_valid_int() -> None:
    """Verify `NonNegativeInt` accepts valid CLI values."""
    assert argutils.NonNegativeInt.type_parser("0") == 0


@pytest.mark.parametrize("arg", ["-1", "1.1", "a"])
def test_non_negative_int_invalid_int(arg: str) -> None:
    """Verify `NonNegativeInt` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.NonNegativeInt.type_parser(arg)


def test_positive_int_range_valid_range() -> None:
    """Verify `PositiveIntRange` accepts valid CLI values."""
    assert argutils.PositiveIntRange.type_parser("1-10") == (1, 10)


@pytest.mark.parametrize("arg", ["-1-10", "1.1-10", "a-10", "1-10.1", "1-a", "2-1", "0-3"])
def test_positive_int_range_invalid_range(arg: str) -> None:
    """Verify `PositiveIntRange` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveIntRange.type_parser(arg)


def test_positive_float_valid_float() -> None:
    """Verify `PositiveFloat` accepts valid CLI values."""
    assert argutils.PositiveFloat.type_parser("1.1") == 1.1


@pytest.mark.parametrize("arg", ["-1.1", "0", "a"])
def test_positive_float_invalid_float(arg: str) -> None:
    """Verify `PositiveFloat` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveFloat.type_parser(arg)


def test_non_negative_float_valid_float() -> None:
    """Verify `NonNegativeFloat` accepts valid CLI values."""
    assert argutils.NonNegativeFloat.type_parser("0") == 0
    assert argutils.NonNegativeFloat.type_parser("1.1") == 1.1


@pytest.mark.parametrize("arg", ["-1.1", "a"])
def test_non_negative_float_invalid_float(arg: str) -> None:
    """Verify `NonNegativeFloat` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.NonNegativeFloat.type_parser(arg)


def test_positive_float_range_valid_range() -> None:
    """Verify `PositiveFloatRange` accepts valid CLI values."""
    assert argutils.PositiveFloatRange.type_parser("1.1-10.1") == (1.1, 10.1)


@pytest.mark.parametrize("arg", ["-1.1-10.1", "a-10.1", "1.1-10.1.1", "1.1-a", "2.1-1.1", "0-3"])
def test_positive_float_range_invalid_range(arg: str) -> None:
    """Verify `PositiveFloatRange` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveFloatRange.type_parser(arg)


def test_non_negative_ratio_valid_ratio() -> None:
    """Verify `NonNegativeRatio` accepts valid CLI values."""
    assert argutils.NonNegativeRatio.type_parser("0.5") == 0.5
    assert argutils.NonNegativeRatio.type_parser("1") == 1
    assert argutils.NonNegativeRatio.type_parser("0") == 0


@pytest.mark.parametrize("arg", ["-1", "1.1", "a"])
def test_non_negative_ratio_invalid_ratio(arg: str) -> None:
    """Verify `NonNegativeRatio` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.NonNegativeRatio.type_parser(arg)


def test_positive_ratio_valid_ratio() -> None:
    """Verify `PositiveRatio` accepts valid CLI values."""
    assert argutils.PositiveRatio.type_parser("0.5") == 0.5
    assert argutils.PositiveRatio.type_parser("1.0") == 1
    assert argutils.PositiveRatio.type_parser("0.01") == 0.01


@pytest.mark.parametrize("arg", ["-1", "1.1", "0", "a"])
def test_positive_ratio_invalid_ratio(arg: str) -> None:
    """Verify `PositiveRatio` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveRatio.type_parser(arg)


def test_gradient_direction_valid_direction() -> None:
    """Verify `GradientDirection` accepts valid CLI values."""
    assert argutils.GradientDirection.type_parser("horizontal") == Gradient.Direction.HORIZONTAL
    assert argutils.GradientDirection.type_parser("vertical") == Gradient.Direction.VERTICAL


def test_gradient_direction_invalid_direction() -> None:
    """Verify `GradientDirection` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.GradientDirection.type_parser("invalid")


def test_color_arg_valid_color() -> None:
    """Verify `ColorArg` accepts valid CLI values."""
    assert argutils.ColorArg.type_parser("125") == Color(125)
    assert argutils.ColorArg.type_parser("ffffff") == Color("#ffffff")


@pytest.mark.parametrize("arg", ["-1", "256", "ffffzz", "aaa"])
def test_color_arg_invalid_color(arg: str) -> None:
    """Verify `ColorArg` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.ColorArg.type_parser(arg)


def test_symbol_valid_symbol() -> None:
    """Verify `Symbol` accepts valid CLI values."""
    assert argutils.Symbol.type_parser("a") == "a"


@pytest.mark.parametrize("arg", ["", "aa"])
def test_symbol_invalid_symbol(arg: str) -> None:
    """Verify `Symbol` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.Symbol.type_parser(arg)


def test_canvas_dimensions_valid_dimension() -> None:
    """Verify `CanvasDimension` accepts valid CLI values."""
    assert argutils.CanvasDimension.type_parser("0") == 0
    assert argutils.CanvasDimension.type_parser("1") == 1
    assert argutils.CanvasDimension.type_parser("-1") == -1


@pytest.mark.parametrize("arg", ["-2", "a", "1.1"])
def test_canvas_dimensions_invalid_dimension(arg: str) -> None:
    """Verify `CanvasDimension` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.CanvasDimension.type_parser(arg)


def test_terminal_dimension_valid_dimension() -> None:
    """Verify `TerminalDimension` accepts valid CLI values."""
    assert argutils.TerminalDimension.type_parser("0") == 0
    assert argutils.TerminalDimension.type_parser("1") == 1


@pytest.mark.parametrize("arg", ["a", "1.1", "-1"])
def test_terminal_dimension_invalid_dimension(arg: str) -> None:
    """Verify `TerminalDimension` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.TerminalDimension.type_parser(arg)


def test_ease_valid_ease() -> None:
    """Verify `Ease` accepts valid CLI values."""
    assert argutils.Ease.type_parser("linear") == easing.linear
    assert argutils.Ease.type_parser("in_sine") == easing.in_sine


def test_ease_invalid_ease() -> None:
    """Verify `Ease` rejects invalid CLI values."""
    with pytest.raises(ArgumentTypeError):
        argutils.Ease.type_parser("invalid")


@pytest.mark.parametrize(
    ("parser", "cli_value", "native_value"),
    [
        (argutils.CharacterGroupArg.type_parser, "row_top_to_bottom", argutils.CharacterGroup.ROW_TOP_TO_BOTTOM),
        (argutils.CharacterSortArg.type_parser, "random", argutils.CharacterSort.RANDOM),
        (argutils.ColorSortArg.type_parser, "random", argutils.ColorSort.RANDOM),
        (argutils.PositiveInt.type_parser, "2", 2),
        (argutils.NonNegativeInt.type_parser, "0", 0),
        (argutils.PositiveIntRange.type_parser, "1-2", (1, 2)),
        (argutils.PositiveFloat.type_parser, "1.5", 1.5),
        (argutils.NonNegativeFloat.type_parser, "0", 0.0),
        (argutils.PositiveFloatRange.type_parser, "0.1-0.2", (0.1, 0.2)),
        (argutils.NonNegativeRatio.type_parser, "0.5", 0.5),
        (argutils.PositiveRatio.type_parser, "0.5", 0.5),
        (argutils.GradientDirection.type_parser, "vertical", Gradient.Direction.VERTICAL),
        (argutils.ColorArg.type_parser, "125", Color(125)),
        (argutils.Symbol.type_parser, "x", "x"),
        (argutils.CanvasDimension.type_parser, "-1", -1),
        (argutils.TerminalDimension.type_parser, "2", 2),
        (argutils.Ease.type_parser, "linear", easing.linear),
        (argutils.EasingStep.type_parser, "0.5", 0.5),
    ],
)
def test_parsers_accept_cli_and_canonical_values(
    parser: Callable[[object], object], cli_value: str, native_value: object
) -> None:
    """Every built-in parser accepts both its CLI spelling and canonical form."""
    assert parser(cli_value) == parser(native_value)


@pytest.mark.parametrize(
    ("parser", "invalid_value"),
    [
        (argutils.PositiveInt.type_parser, True),
        (argutils.NonNegativeInt.type_parser, 1.0),
        (argutils.PositiveIntRange.type_parser, (1, 2.0)),
        (argutils.PositiveFloat.type_parser, True),
        (argutils.PositiveFloatRange.type_parser, (0.1, True)),
        (argutils.ColorArg.type_parser, True),
        (argutils.Symbol.type_parser, 1),
        (argutils.CanvasDimension.type_parser, True),
        (argutils.TerminalDimension.type_parser, 1.5),
        (argutils.EasingStep.type_parser, True),
    ],
)
def test_parsers_reject_invalid_native_values(parser: Callable[[object], object], invalid_value: object) -> None:
    """Native values must meet the same constraints as CLI values."""
    with pytest.raises(ArgumentTypeError):
        parser(invalid_value)
