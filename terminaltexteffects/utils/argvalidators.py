"""Command line argument validators and METAVARs for consistent type parsing and help output.

This module includes a custom formatter for argparse, which combines the features of
`argparse.ArgumentDefaultsHelpFormatter` and `argparse.RawDescriptionHelpFormatter`.

Classes:
    CustomFormatter: A custom formatter for argparse that combines the features of
        `argparse.ArgumentDefaultsHelpFormatter` and `argparse.RawDescriptionHelpFormatter`.
    GradientDirection: Argument type for gradient directions.
    ColorArg: Argument type for color values.
    Symbol: Argument type for single ASCII/UTF-8 characters.
    Ease: Argument type for easing functions.
    PositiveInt: Argument type for positive integers.
    NonNegativeInt: Argument type for nonnegative integers.
    PositiveIntRange: Argument type for integer ranges.
    PositiveFloat: Argument type for positive floats.
    NonNegativeFloat: Argument type for nonnegative floats.
    PositiveFloatRange: Argument type for float ranges.
    TerminalDimension: Argument type for terminal dimensions.
    CanvasDimension: Argument type for canvas dimensions.
    NonNegativeRatio: Argument type for float values between zero and one.
    PositiveRatio: Argument type for positive float values greater than zero and less than or equal to one.
    EasingStep: Argument type for easing step size values.

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
    """Validate argument is a positive integer. n > 0.

    int(n) > 0

    Raises:
        argparse.ArgumentTypeError: Value is not a positive integer.

    """

    METAVAR = "(int > 0)"

    @staticmethod
    def type_parser(arg: str) -> int:
        """Validate argument is a positive integer. n > 0.

        Args:
            arg (str): argument to validate

        Returns:
            int: validated positive integer

        """
        try:
            arg_int = int(arg)

        except ValueError:
            msg = f"invalid value: '{arg}' is not a valid integer."
            raise argparse.ArgumentTypeError(msg) from None

        if arg_int > 0:
            return arg_int
        msg = f"invalid value: '{arg}' is not a valid value. Argument must be an integer > 0."
        raise argparse.ArgumentTypeError(msg)


class NonNegativeInt:
    """Validate argument is a nonnegative integer. n >= 0.

    Raises:
        argparse.ArgumentTypeError: Value is not in range.

    """

    METAVAR = "(int >= 0)"

    @staticmethod
    def type_parser(arg: str) -> int:
        """Validate argument is a nonnegative integer. n >= 0.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not in range.

        Returns:
            int: validated gap value

        """
        try:
            arg_int = int(arg)

        except ValueError:
            msg = f"invalid value: '{arg}' is not a valid integer."
            raise argparse.ArgumentTypeError(msg) from None

        if arg_int < 0:
            msg = f"invalid value: '{arg}' Argument must be int >= 0."
            raise argparse.ArgumentTypeError(msg) from None
        return arg_int


class PositiveIntRange:
    """Validate argument is a valid range of integers n > 0.

    Positive integer ranges are a pair of integers separated by a hyphen. Ex: 1-10

    Example:
        '1-10' is a valid input.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid range of positive integers.

    """

    METAVAR = "(hyphen separated positive int range e.g. '1-10')"

    @staticmethod
    def type_parser(arg: str) -> tuple[int, int]:
        """Validate argument is a valid range of integers n > 0.

        Args:
            arg (str): argument to validate

        Returns:
            tuple[int,int]: validated range

        """
        try:
            start, end = map(int, arg.split("-"))
            if start <= 0:
                msg = f"invalid range: '{arg}' is not a valid range of positive ints. Must be start > 0. Ex: 1-10"
                raise argparse.ArgumentTypeError(
                    msg,
                )
            if start > end:
                msg = f"invalid range: '{arg}' is not a valid range of positive ints. Must be start <= end. Ex: 1-10"
                raise argparse.ArgumentTypeError(
                    msg,
                )

        except ValueError:
            msg = f"invalid range: '{arg}' is not a valid range of positive ints. Must be start-end. Ex: 1-10"
            raise argparse.ArgumentTypeError(
                msg,
            ) from None
        else:
            return start, end


class PositiveFloat:
    """Validate argument is a positive float. n > 0.

    Raises:
        argparse.ArgumentTypeError: Value is not in range.

    """

    METAVAR = "(float > 0)"

    @staticmethod
    def type_parser(arg: str) -> float:
        """Validate argument is a positive float. n > 0.

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
            msg = f"invalid value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg) from None

        if float(arg) > 0:
            return float(arg)
        msg = f"invalid value: '{arg}' is not a valid value. Argument must be a float > 0."
        raise argparse.ArgumentTypeError(msg)


class NonNegativeFloat:
    """Validate argument is a nonnegative float. n >= 0.

    Raises:
        argparse.ArgumentTypeError: Argument value is not in range.

    """

    METAVAR = "(float >= 0)"

    @staticmethod
    def type_parser(arg: str) -> float:
        """Validate argument is a nonnegative float. n >= 0.

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
            msg = f"invalid argument value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg) from None

        if float(arg) < 0:
            msg = f"invalid argument value: '{arg}' is out of range. Must be float >= 0."
            raise argparse.ArgumentTypeError(msg)
        return float(arg)


class PositiveFloatRange:
    """Validate argument is a valid range of positive floats.

    Float ranges are a pair of positive floats separated by a hyphen. Ex: 0.1-1.0

    Raises:
        argparse.ArgumentTypeError: Value is not a valid range of floats.

    """

    METAVAR = "(hyphen separated float range e.g. '0.25-0.5')"

    @staticmethod
    def type_parser(arg: str) -> tuple[float, float]:
        """Validate argument is a valid range of positive floats.

        Args:
            arg (str): argument to validate

        Returns:
            tuple[float,float]: validated range

        """
        try:
            start, end = map(float, arg.split("-"))
            if start > end:
                msg = f"invalid range: '{arg}' is not a valid range of floats. Must be start <= end. Ex: 0.1-1.0"
                raise argparse.ArgumentTypeError(
                    msg,
                )
            if start == 0 or end == 0:
                msg = f"invalid range: '{arg}' is not a valid range of floats. Must be start > 0. Ex: 0.1-1.0"
                raise argparse.ArgumentTypeError(
                    msg,
                )

        except ValueError:
            msg = f"invalid range: '{arg}' is not a valid range. Must be start-end. Ex: 0.1-1.0"
            raise argparse.ArgumentTypeError(msg) from None

        else:
            return start, end


class NonNegativeRatio:
    """Validate argument is a float value between zero and one.

    0 <= float(n) <= 1

    Raises:
        argparse.ArgumentTypeError: Value is not in range.

    """

    METAVAR = "(0 <= float(n) <= 1)"

    @staticmethod
    def type_parser(arg: str) -> float:
        """Validate argument is a float value between zero and one.

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
            msg = f"invalid value: '{arg}' is not a float or int."
            raise argparse.ArgumentTypeError(msg) from None

        if 0 <= float(arg) <= 1:
            return float(arg)
        msg = f"invalid value: '{arg}' is not a float >= 0 and <= 1. Example: 0.5"
        raise argparse.ArgumentTypeError(msg)


class PositiveRatio:
    """Validate argument is a positive float.

    0 < float(n) <= 1

    Raises:
        argparse.ArgumentTypeError: Value is not in range.

    """

    METAVAR = "(0 < float(n) <= 1)"

    @staticmethod
    def type_parser(arg: str) -> float:
        """Validate argument is a positive float.

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
            msg = f"invalid value: '{arg}' is not a float or int."
            raise argparse.ArgumentTypeError(msg) from None

        if 0 < float(arg) <= 1:
            return float(arg)
        msg = f"invalid value: '{arg}' must be 0 < n <=1. Example: 0.5"
        raise argparse.ArgumentTypeError(msg)


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Combine ArgumentDefaultsHelpFormatter and RawDescriptionHelpFormatter for argparse."""


class GradientDirection:
    """Validate argument is a valid gradient direction.

    Raises:
        argparse.ArgumentTypeError: Argument value is not a valid gradient direction.

    """

    METAVAR = "(diagonal, horizontal, vertical, radial)"

    @staticmethod
    def type_parser(arg: str) -> Gradient.Direction:
        """Validate argument is a valid gradient direction.

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
        msg = (
            f"invalid gradient direction: '{arg}' is not a valid gradient direction. Choices are diagonal,"
            " horizontal, vertical, or radial."
        )
        raise argparse.ArgumentTypeError(msg)


class ColorArg:
    """Validate argument is a valid color value.

    Color values can be either an XTerm color value (0-255) or an RGB hex value (000000-ffffff).

    Raises:
        argparse.ArgumentTypeError: Value is not in range of valid XTerm colors or RGB hex colors.

    """

    METAVAR = "(XTerm [0-255] OR RGB Hex [000000-ffffff])"

    @staticmethod
    def type_parser(arg: str) -> Color:
        """Validate argument is a valid color value.

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
                return Color(int(arg))
            except ValueError:
                msg = (
                    f"invalid color value: '{arg}' is not a valid XTerm or RGB color."
                    f" Must be in range {xterm_min}-{xterm_max} or 000000-FFFFFF."
                )
                raise argparse.ArgumentTypeError(msg) from None
        else:
            try:
                return Color(arg)
            except ValueError:
                msg = (
                    f"invalid color value: '{arg}' is not a valid XTerm or RGB color."
                    f" Must be in range {xterm_min}-{xterm_max} or 000000-FFFFFF."
                )
                raise argparse.ArgumentTypeError(msg) from None


class Symbol:
    """Validate argument is a single ASCII/UTF-8 character.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid symbol.

    """

    METAVAR = "(ASCII/UTF-8 character)"

    @staticmethod
    def type_parser(arg: str) -> str:
        """Validate argument is a valid symbol.

        Args:
            arg (str): argument to validate

        Returns:
            str: validated symbol

        """
        if len(arg) == 1 and arg.isprintable():
            return arg
        msg = f"invalid symbol: '{arg}' is not a valid symbol. Must be a single ASCII/UTF-8 character."
        raise argparse.ArgumentTypeError(msg)


class CanvasDimension:
    """Validate argument is a valid canvas dimension.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid canvas dimension.

    """

    METAVAR = "int >= -1"

    @staticmethod
    def type_parser(arg: str) -> int:
        """Validate argument is a valid canvas dimension.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not a valid canvas dimension.

        Returns:
            int: validated canvas dimension

        """
        if arg.isdigit() or arg == "-1":
            return int(arg)
        msg = f"invalid value '{arg}' is not a valid integer. Must be >= -1."
        raise argparse.ArgumentTypeError(msg)


class TerminalDimension:
    """Validate argument is a valid terminal dimension.

    A Terminal Dimension is an integer >= 0.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid terminal dimension.

    """

    METAVAR = "int >= 0"

    @staticmethod
    def type_parser(arg: str) -> int:
        """Validate argument is a valid terminal dimension.

        Args:
            arg (str): argument to validate

        Returns:
            int: validated terminal dimension

        """
        try:
            dimension = int(arg)
            if dimension < 0:
                msg = f"invalid terminal dimensions: '{arg}' is not a valid terminal dimension. Must be >= 0."
                raise argparse.ArgumentTypeError(msg)

        except ValueError:
            msg = f"invalid terminal dimensions: '{arg}' is not a valid terminal dimension. Must be >= 0."
            raise argparse.ArgumentTypeError(msg) from None

        else:
            return dimension


class Ease:
    """Validate argument is a valid easing function.

    Easing functions are prefixed by "in", "out", or "in_out" and suffixed by a valid easing function.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid easing function.

    """

    METAVAR = "(Easing Function)"

    @staticmethod
    def type_parser(arg: str) -> typing.Callable:
        """Validate argument is a valid easing function.

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
            msg = f"invalid ease value: '{arg}' is not a valid ease."
            raise argparse.ArgumentTypeError(msg) from None


class EasingStep:
    """Validate argument is a valid easing step size value.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid easing step size.

    """

    METAVAR = "0 < float(n) <= 1"

    @staticmethod
    def type_parser(arg: str) -> float:
        """Validate argument is a valid easing step size value.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not a valid easing step size.

        Returns:
            float: validated easing step size value

        """
        try:
            f = float(arg)
        except ValueError:
            msg = f"invalid value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg) from None

        if 0 < f <= 1:
            return f
        msg = f"invalid value: '{arg}' is not a float > 0 and <= 1. Example: 0.5"
        raise argparse.ArgumentTypeError(msg)
