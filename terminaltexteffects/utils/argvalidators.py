"""
This module provides command line argument validators and METAVARs for consistent type parsing and help output.

It includes a custom formatter for argparse, which combines the features of
`argparse.ArgumentDefaultsHelpFormatter` and `argparse.RawDescriptionHelpFormatter`.

Classes:
    CustomFormatter: A custom formatter for argparse that combines the features of
        `argparse.ArgumentDefaultsHelpFormatter` and `argparse.RawDescriptionHelpFormatter`.
    GradientDirection: Argument type for gradient directions.
    Color: Argument type for color values.
    Symbol: Argument type for single ASCII/UTF-8 characters.
    Ease: Argument type for easing functions.
    PositiveInt: Argument type for positive integers.
    NonNegativeInt: Argument type for nonnegative integers.
    IntRange: Argument type for integer ranges.
    PositiveFloat: Argument type for positive floats.
    NonNegativeFloat: Argument type for nonnegative floats.
    PositiveFloatRange: Argument type for float ranges.
    TerminalDimensions: Argument type for terminal dimensions.
    CanvasDimension: Argument type for canvas dimensions.
    Ratio: Argument type for float values between zero and one.


Functions:
    is_ascii_or_utf8: Tests if the given string is either ASCII or UTF-8.

Constants:
    EASING_EPILOG (str): A detailed description of the easing functions supported.
"""

from __future__ import annotations

import argparse
import typing

from terminaltexteffects.utils import easing
from terminaltexteffects.utils.graphics import Color, Gradient

EASING_EPILOG = """\
    Easing
    ------
    Note: A prefix must be added to the function name (except LINEAR).
    
    All easing functions support the following prefixes:
        IN_  - Ease in
        OUT_ - Ease out
        IN_OUT_ - Ease in and out
        
    Easing Functions
    ----------------
    LINEAR - Linear easing
    SINE   - Sine easing
    QUAD   - Quadratic easing
    CUBIC  - Cubic easing
    QUART  - Quartic easing
    QUINT  - Quintic easing
    EXPO   - Exponential easing
    CIRC   - Circular easing
    BACK   - Back easing
    ELASTIC - Elastic easing
    BOUNCE - Bounce easing
    
    Visit: https://easings.net/ for visualizations of the easing functions.
"""


class PositiveInt:
    """Argument type for positive integers.

    int(n) > 0

    Raises:
        argparse.ArgumentTypeError: Value is not a positive integer.
    """

    METAVAR = "(int > 0)"

    @staticmethod
    def type_parser(arg: str) -> int:
        """Validates that the given argument is a positive integer. n > 0.

        Args:
            arg (str): argument to validate

        Returns:
            int: validated positive integer
        """
        try:
            int(arg)

        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid value: '{arg}' is not a valid integer.")

        if int(arg) > 0:
            return int(arg)
        else:
            raise argparse.ArgumentTypeError(f"invalid value: '{arg}' is not > 0.")


class NonNegativeInt:
    """Validates that the given argument is a nonnegative integer. n >= 0.

    Raises:
        argparse.ArgumentTypeError: Value is not in range.
    """

    METAVAR = "(int >= 0)"

    @staticmethod
    def type_parser(arg: str) -> int:
        """Validates that the given argument is a nonnegative integer. n >= 0.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not in range.

        Returns:
            int: validated gap value
        """
        try:
            int(arg)

        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid value: '{arg}' is not a valid integer.")

        if int(arg) < 0:
            raise argparse.ArgumentTypeError(f"invalid value: '{arg}' Argument must be int >= 0.")
        return int(arg)


class PositiveIntRange:
    """Argument type for positive integer ranges.

    Positive integer ranges are a pair of integers separated by a hyphen. Ex: 1-10

    Raises:
        argparse.ArgumentTypeError: Value is not a valid range of positive integers.
    """

    METAVAR = "(hyphen separated positive int range e.g. '1-10')"

    @staticmethod
    def type_parser(arg: str) -> tuple[int, int]:
        """Validates that the given argument is a valid range of integers n > 0.

        Args:
            arg (str): argument to validate

        Returns:
            tuple[int,int]: validated range
        """
        try:
            start, end = map(int, arg.split("-"))
            if start <= 0:
                raise argparse.ArgumentTypeError(
                    f"invalid range: '{arg}' is not a valid range of positive ints. Must be start > 0. Ex: 1-10"
                )
            if start > end:
                raise argparse.ArgumentTypeError(
                    f"invalid range: '{arg}' is not a valid range of positive ints. Must be start <= end. Ex: 1-10"
                )
            return start, end
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"invalid range: '{arg}' is not a valid range of positive ints. Must be start-end. Ex: 1-10"
            )


class PositiveFloat:
    """Validates that the given argument is a positive float. n > 0.

    Raises:
        argparse.ArgumentTypeError: Value is not in range.
    """

    METAVAR = "(float > 0)"

    @staticmethod
    def type_parser(arg: str) -> float:
        """Validates that the given argument is a positive float. n > 0.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: value is not in range.

        Returns:
            float: validated positive float
        """
        try:
            float(arg)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid value: '{arg}' is not a valid float.")

        if float(arg) > 0:
            return float(arg)
        else:
            raise argparse.ArgumentTypeError(
                f"invalid value: '{arg}' is not a valid value. Argument must be a float > 0."
            )


class NonNegativeFloat:
    """Validates that the given argument is a valid animationrate value. n >= 0.

    Raises:
        argparse.ArgumentTypeError: Argument value is not in range.
    """

    METAVAR = "(float >= 0)"

    @staticmethod
    def type_parser(arg: str) -> float:
        """Validates that the given argument is a valid animationrate value. n >= 0.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Argument value is not in range.

        Returns:
            float: validated value
        """
        try:
            float(arg)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid argument value: '{arg}' is not a valid float.")

        if float(arg) < 0:
            raise argparse.ArgumentTypeError(f"invalid argument value: '{arg}' is out of range. Must be float >= 0.")
        return float(arg)


class PositiveFloatRange:
    """Argument type for float ranges.

    Float ranges are a pair of positive floats separated by a hyphen. Ex: 0.1-1.0

    Raises:
        argparse.ArgumentTypeError: Value is a valid range of floats.
    """

    METAVAR = "(hyphen separated float range e.g. '0.25-0.5')"

    @staticmethod
    def type_parser(arg: str) -> tuple[float, float]:
        """Validates that the given argument is a valid range of floats n >= 0.

        Args:
            arg (str): argument to validate

        Returns:
            tuple[float,float]: validated range
        """
        try:
            start, end = map(float, arg.split("-"))
            if start > end:
                raise argparse.ArgumentTypeError(
                    f"invalid range: '{arg}' is not a valid range of floats. Must be start <= end. Ex: 0.1-1.0"
                )
            elif start == 0 or end == 0:
                raise argparse.ArgumentTypeError(
                    f"invalid range: '{arg}' is not a valid range of floats. Must be start > 0. Ex: 0.1-1.0"
                )
            return start, end
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"invalid range: '{arg}' is not a valid range. Must be start-end. Ex: 0.1-1.0"
            )


class Ratio:
    """Validates that the given argument is a valid float value between zero and one.

    0 <= float(n) <= 1

    Raises:
        argparse.ArgumentTypeError: Value is not in range.
    """

    METAVAR = "(0 <= float(n) <= 1)"

    @staticmethod
    def type_parser(arg: str) -> float:
        """Validates that the given argument is a valid float value between zero and one.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not in range.

        Returns:
            float: validated float value
        """
        try:
            float(arg)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid value: '{arg}' is not a float or int.")

        if 0 <= float(arg) <= 1:
            return float(arg)
        else:
            raise argparse.ArgumentTypeError(f"invalid value: '{arg}' is not a float >= 0 and <= 1. Example: 0.5")


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Custom formatter for argparse that combines ArgumentDefaultsHelpFormatter and RawDescriptionHelpFormatter."""

    pass


class GradientDirection:
    """Argument type for gradient directions.

    Raises:
        argparse.ArgumentTypeError: Argument value is not a valid gradient direction.
    """

    METAVAR = "(diagonal, horizontal, vertical, radial)"

    @staticmethod
    def type_parser(arg: str) -> Gradient.Direction:
        """Validates that the given argument is a valid gradient direction.

        Args:
            arg (str): argument to validate

        Returns:
            Gradient.Direction: validated gradient direction

        Raises:
            argparse.ArgumentTypeError: Argument value is not a valid gradient direction.
        """
        direction_map = {
            "horizontal": Gradient.Direction.HORIZONTAL,
            "vertical": Gradient.Direction.VERTICAL,
            "diagonal": Gradient.Direction.DIAGONAL,
            "radial": Gradient.Direction.RADIAL,
        }
        if arg.lower() in direction_map:
            return direction_map[arg.lower()]
        else:
            raise argparse.ArgumentTypeError(
                f"invalid gradient direction: '{arg}' is not a valid gradient direction. Choices are diagonal, horizontal, vertical, or radial."
            )


class ColorArg:
    """Argument type for color values.

    Color values can be either an XTerm color value (0-255) or an RGB hex value (000000-ffffff).

    Raises:
        argparse.ArgumentTypeError: Value is not in range of valid XTerm colors or RGB hex colors.
    """

    METAVAR = "(XTerm [0-255] OR RGB Hex [000000-ffffff])"

    @staticmethod
    def type_parser(arg: str) -> Color:
        """Validates that the given argument is a valid color value.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Color value is not in range.

        Returns:
            Color : validated color value
        """
        xterm_min = 0
        xterm_max = 255
        if len(arg) <= 3:
            try:
                color = Color(int(arg))
                return color
            except ValueError:
                raise argparse.ArgumentTypeError(
                    f"invalid color value: '{arg}' is not a valid XTerm or RGB color. Must be in range {xterm_min}-{xterm_max} or 000000-FFFFFF."
                )
        else:
            try:
                color = Color(arg)
                return color
            except ValueError:
                raise argparse.ArgumentTypeError(
                    f"invalid color value: '{arg}' is not a valid XTerm or RGB color. Must be in range {xterm_min}-{xterm_max} or 000000-FFFFFF."
                )


class Symbol:
    """Argument type for single ASCII/UTF-8 characters.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid symbol.
    """

    METAVAR = "(ASCII/UTF-8 character)"

    @staticmethod
    def type_parser(arg: str) -> str:
        """Validates that the given argument is a valid symbol.

        Args:
            arg (str): argument to validate

        Returns:
            str: validated symbol
        """
        if len(arg) == 1 and arg.isprintable():
            return arg
        else:
            raise argparse.ArgumentTypeError(
                f"invalid symbol: '{arg}' is not a valid symbol. Must be a single ASCII/UTF-8 character."
            )


class CanvasDimension:
    """Argument type for canvas dimensions.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid canvas dimension.
    """

    METAVAR = "int >= -1"

    @staticmethod
    def type_parser(arg: str) -> int:
        """Validates that the given argument is a valid canvas dimension.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not a valid canvas dimension.

        Returns:
            int: validated canvas dimension
        """
        if arg.isdigit() or arg == "-1":
            return int(arg)
        else:
            raise argparse.ArgumentTypeError(f"invalid value '{arg}' is not a valid integer. Must be >= -1.")


class TerminalDimension:
    """Argument type for terminal dimension.

    A Terminal Dimension is an integer >= 0.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid terminal dimension.
    """

    METAVAR = "int >= 0"

    @staticmethod
    def type_parser(arg: str) -> int:
        """Validates that the given argument is a valid terminal dimension.

        Args:
            arg (str): argument to validate

        Returns:
            int: validated terminal dimension
        """
        try:
            dimension = int(arg)
            if dimension < 0:
                raise argparse.ArgumentTypeError(
                    f"invalid terminal dimensions: '{arg}' is not a valid terminal dimension. Must be >= 0."
                )
            return dimension
        except ValueError:
            raise argparse.ArgumentTypeError(
                f"invalid terminal dimensions: '{arg}' is not a valid terminal dimension. Must be >= 0."
            )


class Ease:
    """Argument type for easing functions.

    Easing functions are prefixed by "in", "out", or "in_out" and suffixed by a valid easing function.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid easing function.
    """

    METAVAR = "(Easing Function)"

    @staticmethod
    def type_parser(arg: str) -> typing.Callable:
        """Validates that the given argument is a valid easing function.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Ease value is not a valid easing function.

        Returns:
            Ease: validated ease value
        """
        easing_func_map = {
            "linear": easing.linear,
            "in_sine": easing.in_sine,
            "out_sine": easing.out_sine,
            "in_out_sine": easing.in_out_sine,
            "in_quad": easing.in_quad,
            "out_quad": easing.out_quad,
            "in_out_quad": easing.in_out_quad,
            "in_cubic": easing.in_cubic,
            "out_cubic": easing.out_cubic,
            "in_out_cubic": easing.in_out_cubic,
            "in_quart": easing.in_quart,
            "out_quart": easing.out_quart,
            "in_out_quart": easing.in_out_quart,
            "in_quint": easing.in_quint,
            "out_quint": easing.out_quint,
            "in_out_quint": easing.in_out_quint,
            "in_expo": easing.in_expo,
            "out_expo": easing.out_expo,
            "in_out_expo": easing.in_out_expo,
            "in_circ": easing.in_circ,
            "out_circ": easing.out_circ,
            "in_out_circ": easing.in_out_circ,
            "in_back": easing.in_back,
            "out_back": easing.out_back,
            "in_out_back": easing.in_out_back,
            "in_elastic": easing.in_elastic,
            "out_elastic": easing.out_elastic,
            "in_out_elastic": easing.in_out_elastic,
            "in_bounce": easing.in_bounce,
            "out_bounce": easing.out_bounce,
            "in_out_bounce": easing.in_out_bounce,
        }

        try:
            return easing_func_map[arg.lower()]
        except KeyError:
            raise argparse.ArgumentTypeError(f"invalid ease value: '{arg}' is not a valid ease.")
