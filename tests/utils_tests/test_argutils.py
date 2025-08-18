from argparse import ArgumentTypeError

import pytest

from terminaltexteffects.utils import argutils, easing
from terminaltexteffects.utils.graphics import Color, Gradient

pytestmark = [pytest.mark.utils, pytest.mark.smoke]


def test_postive_int_valid_int():
    assert argutils.PositiveInt.type_parser("1") == 1


@pytest.mark.parametrize("arg", ["-1", "0", "1.1", "a"])
def test_postive_int_invalid_int(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveInt.type_parser(arg)


def test_non_negative_int_valid_int():
    assert argutils.NonNegativeInt.type_parser("0") == 0


@pytest.mark.parametrize("arg", ["-1", "1.1", "a"])
def test_non_negative_int_invalid_int(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.NonNegativeInt.type_parser(arg)


def test_positive_int_range_valid_range():
    assert argutils.PositiveIntRange.type_parser("1-10") == (1, 10)


@pytest.mark.parametrize("arg", ["-1-10", "1.1-10", "a-10", "1-10.1", "1-a", "2-1", "0-3"])
def test_positive_int_range_invalid_range(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveIntRange.type_parser(arg)


def test_positive_float_valid_float():
    assert argutils.PositiveFloat.type_parser("1.1") == 1.1


@pytest.mark.parametrize("arg", ["-1.1", "0", "a"])
def test_positive_float_invalid_float(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveFloat.type_parser(arg)


def test_non_negative_float_valid_float():
    assert argutils.NonNegativeFloat.type_parser("0") == 0
    assert argutils.NonNegativeFloat.type_parser("1.1") == 1.1


@pytest.mark.parametrize("arg", ["-1.1", "a"])
def test_non_negative_float_invalid_float(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.NonNegativeFloat.type_parser(arg)


def test_positive_float_range_valid_range():
    assert argutils.PositiveFloatRange.type_parser("1.1-10.1") == (1.1, 10.1)


@pytest.mark.parametrize("arg", ["-1.1-10.1", "a-10.1", "1.1-10.1.1", "1.1-a", "2.1-1.1", "0-3"])
def test_positive_float_range_invalid_range(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveFloatRange.type_parser(arg)


def test_NonNegativeRatio_valid_ratio():
    assert argutils.NonNegativeRatio.type_parser("0.5") == 0.5
    assert argutils.NonNegativeRatio.type_parser("1") == 1
    assert argutils.NonNegativeRatio.type_parser("0") == 0


@pytest.mark.parametrize("arg", ["-1", "1.1", "a"])
def test_NonNegativeRatio_invalid_ratio(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.NonNegativeRatio.type_parser(arg)


def test_PositiveRatio_valid_ratio():
    assert argutils.PositiveRatio.type_parser("0.5") == 0.5
    assert argutils.PositiveRatio.type_parser("1.0") == 1
    assert argutils.PositiveRatio.type_parser("0.01") == 0.01


@pytest.mark.parametrize("arg", ["-1", "1.1", "0", "a"])
def test_PositiveRatio_invalid_ratio(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.PositiveRatio.type_parser(arg)


def test_gradient_direction_valid_direction():
    assert argutils.GradientDirection.type_parser("horizontal") == Gradient.Direction.HORIZONTAL
    assert argutils.GradientDirection.type_parser("vertical") == Gradient.Direction.VERTICAL


def test_gradient_direction_invalid_direction():
    with pytest.raises(ArgumentTypeError):
        argutils.GradientDirection.type_parser("invalid")


def test_color_arg_valid_color():
    assert argutils.ColorArg.type_parser("125") == Color(125)
    assert argutils.ColorArg.type_parser("ffffff") == Color("ffffff")


@pytest.mark.parametrize("arg", ["-1", "256", "ffffzz", "aaa"])
def test_color_arg_invalid_color(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.ColorArg.type_parser(arg)


def test_symbol_valid_symbol():
    assert argutils.Symbol.type_parser("a") == "a"


@pytest.mark.parametrize("arg", ["", "aa"])
def test_symbol_invalid_symbol(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.Symbol.type_parser(arg)


def test_canvas_dimensions_valid_dimension():
    assert argutils.CanvasDimension.type_parser("0") == 0
    assert argutils.CanvasDimension.type_parser("1") == 1
    assert argutils.CanvasDimension.type_parser("-1") == -1


@pytest.mark.parametrize("arg", ["-2", "a", "1.1"])
def test_canvas_dimensions_invalid_dimension(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.CanvasDimension.type_parser(arg)


def test_terminal_dimension_valid_dimension():
    assert argutils.TerminalDimension.type_parser("0") == 0
    assert argutils.TerminalDimension.type_parser("1") == 1


@pytest.mark.parametrize("arg", ["a", "1.1", "-1"])
def test_terminal_dimension_invalid_dimension(arg):
    with pytest.raises(ArgumentTypeError):
        argutils.TerminalDimension.type_parser(arg)


def test_ease_valid_ease():
    assert argutils.Ease.type_parser("linear") == easing.linear
    assert argutils.Ease.type_parser("in_sine") == easing.in_sine


def test_ease_invalid_ease():
    with pytest.raises(ArgumentTypeError):
        argutils.Ease.type_parser("invalid")
