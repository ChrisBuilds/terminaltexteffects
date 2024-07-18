import pytest
from terminaltexteffects.utils import argvalidators, easing
from terminaltexteffects.utils.graphics import Gradient, Color
from argparse import ArgumentTypeError


def test_postive_int_valid_int():
    assert argvalidators.PositiveInt.type_parser("1") == 1


@pytest.mark.parametrize("arg", ["-1", "0", "1.1", "a"])
def test_postive_int_invalid_int(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.PositiveInt.type_parser(arg)


def test_non_negative_int_valid_int():
    assert argvalidators.NonNegativeInt.type_parser("0") == 0


@pytest.mark.parametrize("arg", ["-1", "1.1", "a"])
def test_non_negative_int_invalid_int(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.NonNegativeInt.type_parser(arg)


def test_positive_int_range_valid_range():
    assert argvalidators.PositiveIntRange.type_parser("1-10") == (1, 10)


@pytest.mark.parametrize("arg", ["-1-10", "1.1-10", "a-10", "1-10.1", "1-a", "2-1", "0-3"])
def test_positive_int_range_invalid_range(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.PositiveIntRange.type_parser(arg)


def test_positive_float_valid_float():
    assert argvalidators.PositiveFloat.type_parser("1.1") == 1.1


@pytest.mark.parametrize("arg", ["-1.1", "0", "a"])
def test_positive_float_invalid_float(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.PositiveFloat.type_parser(arg)


def test_non_negative_float_valid_float():
    assert argvalidators.NonNegativeFloat.type_parser("0") == 0
    assert argvalidators.NonNegativeFloat.type_parser("1.1") == 1.1


@pytest.mark.parametrize("arg", ["-1.1", "a"])
def test_non_negative_float_invalid_float(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.NonNegativeFloat.type_parser(arg)


def test_positive_float_range_valid_range():
    assert argvalidators.PositiveFloatRange.type_parser("1.1-10.1") == (1.1, 10.1)


@pytest.mark.parametrize("arg", ["-1.1-10.1", "a-10.1", "1.1-10.1.1", "1.1-a", "2.1-1.1", "0-3"])
def test_positive_float_range_invalid_range(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.PositiveFloatRange.type_parser(arg)


def test_ratio_valid_ratio():
    assert argvalidators.Ratio.type_parser("0.5") == 0.5
    assert argvalidators.Ratio.type_parser("1") == 1
    assert argvalidators.Ratio.type_parser("0") == 0


@pytest.mark.parametrize("arg", ["-1", "1.1", "a"])
def test_ratio_invalid_ratio(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.Ratio.type_parser(arg)


def test_gradient_direction_valid_direction():
    assert argvalidators.GradientDirection.type_parser("horizontal") == Gradient.Direction.HORIZONTAL
    assert argvalidators.GradientDirection.type_parser("vertical") == Gradient.Direction.VERTICAL


def test_gradient_direction_invalid_direction():
    with pytest.raises(ArgumentTypeError):
        argvalidators.GradientDirection.type_parser("invalid")


def test_color_arg_valid_color():
    assert argvalidators.ColorArg.type_parser("125") == Color(125)
    assert argvalidators.ColorArg.type_parser("ffffff") == Color("ffffff")


@pytest.mark.parametrize("arg", ["-1", "256", "ffffzz", "aaa"])
def test_color_arg_invalid_color(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.ColorArg.type_parser(arg)


def test_symbol_valid_symbol():
    assert argvalidators.Symbol.type_parser("a") == "a"


@pytest.mark.parametrize("arg", ["", "aa"])
def test_symbol_invalid_symbol(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.Symbol.type_parser(arg)


def test_canvas_dimensions_valid_dimension():
    assert argvalidators.CanvasDimension.type_parser("0") == 0
    assert argvalidators.CanvasDimension.type_parser("1") == 1
    assert argvalidators.CanvasDimension.type_parser("-1") == -1


@pytest.mark.parametrize("arg", ["-2", "a", "1.1"])
def test_canvas_dimensions_invalid_dimension(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.CanvasDimension.type_parser(arg)


def test_terminal_dimension_valid_dimension():
    assert argvalidators.TerminalDimension.type_parser("0") == 0
    assert argvalidators.TerminalDimension.type_parser("1") == 1


@pytest.mark.parametrize("arg", ["a", "1.1", "-1"])
def test_terminal_dimension_invalid_dimension(arg):
    with pytest.raises(ArgumentTypeError):
        argvalidators.TerminalDimension.type_parser(arg)


def test_ease_valid_ease():
    assert argvalidators.Ease.type_parser("linear") == easing.linear
    assert argvalidators.Ease.type_parser("in_sine") == easing.in_sine


def test_ease_invalid_ease():
    with pytest.raises(ArgumentTypeError):
        argvalidators.Ease.type_parser("invalid")
