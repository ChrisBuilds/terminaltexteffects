"""Command line argument validators and METAVARs for consistent type parsing and help output.

This module includes a custom formatter for argparse, which combines the features of
`argparse.ArgumentDefaultsHelpFormatter` and `argparse.RawDescriptionHelpFormatter`.

Classes:
    CustomFormatter: A custom formatter for argparse that combines the features of
        `argparse.ArgumentDefaultsHelpFormatter` and `argparse.RawDescriptionHelpFormatter`.
    CharacterGroup: An enum specifying character groupings.
    CharacterGroupArg: Argument type for character groupings.
    CharacterSort: An enum specifying character sorts.
    CharacterSortArg: Argument type for character sorts.
    ColorSort: An enum specifying color sorts.
    ColorSortArg: Argument type for color sorts.
    TupleAction: Custom argparse action to convert a list of values into a tuple.
    ParserSpec: Specification for a parser in the argument parser.
    ArgSpec: Specification for a command-line argument and default value.
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

Constants:
    EASING_EPILOG (str): A detailed description of the easing functions supported.
"""

from __future__ import annotations

import argparse
import typing
from dataclasses import dataclass
from enum import Enum, auto

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

_MISSING = object()


def format_cli_default(value: typing.Any, type_parser: typing.Any = _MISSING) -> str:
    """Format a canonical value using its equivalent command-line spelling.

    This is the fallback used for argument defaults when an `ArgSpec` does not
    provide a more specific `default_formatter`.
    """
    if type_parser in (PositiveIntRange.type_parser, PositiveFloatRange.type_parser):
        return format_cli_range(value)
    if isinstance(value, Color):
        return str(value.color_arg)
    if isinstance(value, Enum):
        return value.name.lower()
    if isinstance(value, (tuple, list)):
        return " ".join(format_cli_default(item) for item in value)
    if callable(value):
        return value.__name__
    return str(value)


def format_cli_range(value: tuple[int, int] | tuple[float, float]) -> str:
    """Format a two-value range using the hyphenated command-line syntax."""
    return f"{value[0]}-{value[1]}"


@dataclass(frozen=True)
class ParserSpec:
    """Specification for creating an argparse subparser for an effect config.

    Each field maps directly to keyword arguments passed to
    `argparse._SubParsersAction.add_parser()`.
    """

    name: str
    help: str
    description: str
    epilog: str


@dataclass(frozen=True)
class ArgSpec:
    """Specification for a command-line argument and config default value.

    Non-missing fields map directly to keyword arguments for
    `argparse.ArgumentParser.add_argument()`. The `default` value is also used by
    `BaseConfig._build_config()` when constructing configs without parsed CLI input.

    The `type` callable is the normalization contract shared by CLI parsing and
    library configuration. Custom callables must accept both CLI strings and
    values that are already in their canonical library form.

    `default_formatter`, when supplied, formats the canonical default for CLI
    help text only. It does not affect parsing or configuration construction.
    """

    name: str
    default: typing.Any
    metavar: str = _MISSING  # type: ignore[arg-type]
    type: typing.Any = _MISSING  # type: ignore[arg-type]
    required: bool = _MISSING  # type: ignore[arg-type]
    help: str = _MISSING  # type: ignore[arg-type]
    action: str | type[argparse.Action] = _MISSING  # type: ignore[arg-type]
    choices: list[typing.Any] = _MISSING  # type: ignore[arg-type]
    nargs: str | int = _MISSING  # type: ignore[arg-type]
    default_formatter: typing.Callable[[typing.Any], str] = _MISSING  # type: ignore[assignment]

    def normalize(self, value: typing.Any) -> typing.Any:
        """Normalize and validate a configuration value described by this spec."""
        if self.action == "store_true":
            if not isinstance(value, bool):
                msg = f"invalid value: '{value}' must be a boolean."
                raise argparse.ArgumentTypeError(msg)
            return value

        values = value if self.action is TupleAction and isinstance(value, (list, tuple)) else (value,)
        if self.action is TupleAction:
            return tuple(self._normalize_scalar(item) for item in values)
        return self._normalize_scalar(value)

    def _normalize_scalar(self, value: typing.Any) -> typing.Any:
        normalized = self.type(value) if self.type is not _MISSING else value
        if self.choices is not _MISSING and normalized not in self.choices:
            msg = f"invalid choice: '{normalized}' (choose from {', '.join(map(str, self.choices))})"
            raise argparse.ArgumentTypeError(msg)
        return normalized


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Combine ArgumentDefaultsHelpFormatter and RawDescriptionHelpFormatter for argparse."""

    def _get_help_string(self, action: argparse.Action) -> str:
        """Return help text with defaults rendered as command-line values."""
        help_string = super()._get_help_string(action) or ""
        default_formatter = getattr(action, "default_formatter", None)
        if default_formatter is None:
            default_value = format_cli_default(action.default, action.type)
        else:
            default_value = default_formatter(action.default)
        default_value = default_value.replace("%", "%%")
        return help_string.replace("%(default)s", default_value)


class CharacterGroup(Enum):
    """An enum specifying character groupings."""

    COLUMN_LEFT_TO_RIGHT = auto()
    COLUMN_RIGHT_TO_LEFT = auto()
    ROW_TOP_TO_BOTTOM = auto()
    ROW_BOTTOM_TO_TOP = auto()
    DIAGONAL_TOP_LEFT_TO_BOTTOM_RIGHT = auto()
    DIAGONAL_BOTTOM_LEFT_TO_TOP_RIGHT = auto()
    DIAGONAL_TOP_RIGHT_TO_BOTTOM_LEFT = auto()
    DIAGONAL_BOTTOM_RIGHT_TO_TOP_LEFT = auto()
    CENTER_TO_OUTSIDE = auto()
    OUTSIDE_TO_CENTER = auto()


class CharacterGroupArg:
    """Validate argument is a valid CharacterGroup.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid CharacterGroup.

    """

    METAVAR = tuple(n.lower() for n in CharacterGroup._member_names_)

    @staticmethod
    def type_parser(arg: str | CharacterGroup) -> CharacterGroup:
        """Validate argument is a valid CharacterGroup.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not a valid CharacterGroup.

        Returns:
            CharacterGroup: validated CharacterGroup

        """
        if isinstance(arg, CharacterGroup):
            return arg
        try:
            return CharacterGroup[arg.upper()]
        except (AttributeError, KeyError):
            msg = f"invalid CharacterGroup: '{arg}' is not a valid CharacterGroup."
            raise argparse.ArgumentTypeError(msg) from None


class CharacterSort(Enum):
    """An enum for specifying character sorts."""

    RANDOM = auto()
    TOP_TO_BOTTOM_LEFT_TO_RIGHT = auto()
    TOP_TO_BOTTOM_RIGHT_TO_LEFT = auto()
    BOTTOM_TO_TOP_LEFT_TO_RIGHT = auto()
    BOTTOM_TO_TOP_RIGHT_TO_LEFT = auto()
    OUTSIDE_ROW_TO_MIDDLE = auto()
    MIDDLE_ROW_TO_OUTSIDE = auto()


class CharacterSortArg:
    """Validate argument is a valid CharacterSort.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid CharacterSort.

    """

    METAVAR = tuple(n.lower() for n in CharacterSort._member_names_)

    @staticmethod
    def type_parser(arg: str | CharacterSort) -> CharacterSort:
        """Validate argument is a valid CharacterSort.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not a valid CharacterSort.

        Returns:
            CharacterSort: validated CharacterSort

        """
        if isinstance(arg, CharacterSort):
            return arg
        try:
            return CharacterSort[arg.upper()]
        except (AttributeError, KeyError):
            msg = f"invalid CharacterSort: '{arg}' is not a valid CharacterSort."
            raise argparse.ArgumentTypeError(msg) from None


class ColorSort(Enum):
    """An enum for specifying color sorts for the colors derived from the input text ansi sequences."""

    LEAST_TO_MOST = auto()
    MOST_TO_LEAST = auto()
    RANDOM = auto()


class ColorSortArg:
    """Validate argument is a valid ColorSort.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid ColorSort.

    """

    METAVAR = tuple(n.lower() for n in ColorSort._member_names_)

    @staticmethod
    def type_parser(arg: str | ColorSort) -> ColorSort:
        """Validate argument is a valid ColorSort.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not a valid ColorSort.

        Returns:
            ColorSort: validated ColorSort

        """
        if isinstance(arg, ColorSort):
            return arg
        try:
            return ColorSort[arg.upper()]
        except (AttributeError, KeyError):
            msg = f"invalid ColorSort: '{arg}' is not a valid ColorSort."
            raise argparse.ArgumentTypeError(msg) from None


class TupleAction(argparse.Action):
    """Convert parsed multi-value arguments into tuples.

    Used for arguments that accept multiple values via `nargs`. If argparse provides
    `None`, the destination is set to an empty tuple.
    """

    def __call__(
        self,
        _: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: typing.Sequence[typing.Any] | None,
        __: str | None = None,
    ) -> None:
        """Convert a list of values into a tuple."""
        if values is None:
            setattr(namespace, self.dest, ())
            return
        setattr(namespace, self.dest, tuple(values))


class PositiveInt:
    """Validate argument is a positive integer. n > 0.

    int(n) > 0

    Raises:
        argparse.ArgumentTypeError: Value is not a positive integer.

    """

    METAVAR = "(int > 0)"

    @staticmethod
    def type_parser(arg: str | int) -> int:
        """Validate argument is a positive integer. n > 0.

        Args:
            arg (str): argument to validate

        Returns:
            int: validated positive integer

        """
        if isinstance(arg, bool) or not isinstance(arg, (str, int)):
            msg = f"invalid value: '{arg}' is not a valid integer."
            raise argparse.ArgumentTypeError(msg)
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
    def type_parser(arg: str | int) -> int:
        """Validate argument is a nonnegative integer. n >= 0.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not in range.

        Returns:
            int: validated gap value

        """
        if isinstance(arg, bool) or not isinstance(arg, (str, int)):
            msg = f"invalid value: '{arg}' is not a valid integer."
            raise argparse.ArgumentTypeError(msg)
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
    """Validate argument is a nondecreasing range that starts with a positive integer.

    Positive integer ranges are expressed as two integers separated by a hyphen,
    for example `1-10`.

    Example:
        '1-10' is a valid input.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid positive integer range.

    """

    METAVAR = "(hyphen separated positive int range e.g. '1-10')"

    @staticmethod
    def type_parser(arg: str | tuple[int, int] | list[int]) -> tuple[int, int]:
        """Validate argument is a valid range of integers n > 0.

        Args:
            arg (str): argument to validate

        Returns:
            tuple[int,int]: validated range

        """
        try:
            if isinstance(arg, (tuple, list)):
                if len(arg) != 2 or any(isinstance(value, bool) or not isinstance(value, int) for value in arg):
                    msg = f"invalid range: '{arg}' is not a valid range of positive ints. Must be start-end. Ex: 1-10"
                    raise argparse.ArgumentTypeError(msg)
                start, end = arg
            else:
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

        except (AttributeError, ValueError):
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
    def type_parser(arg: str | float) -> float:
        """Validate argument is a positive float. n > 0.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: value is not in range.

        Returns:
            float: validated positive float

        """
        if isinstance(arg, bool) or not isinstance(arg, (str, int, float)):
            msg = f"invalid value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg)
        try:
            arg_float = float(arg)
        except ValueError:
            msg = f"invalid value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg) from None

        if arg_float > 0:
            return arg_float
        msg = f"invalid value: '{arg}' is not a valid value. Argument must be a float > 0."
        raise argparse.ArgumentTypeError(msg)


class NonNegativeFloat:
    """Validate argument is a nonnegative float. n >= 0.

    Raises:
        argparse.ArgumentTypeError: Argument value is not in range.

    """

    METAVAR = "(float >= 0)"

    @staticmethod
    def type_parser(arg: str | float) -> float:
        """Validate argument is a nonnegative float. n >= 0.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Argument value is not in range.

        Returns:
            float: validated value

        """
        if isinstance(arg, bool) or not isinstance(arg, (str, int, float)):
            msg = f"invalid argument value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg)
        try:
            arg_float = float(arg)
        except ValueError:
            msg = f"invalid argument value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg) from None

        if arg_float < 0:
            msg = f"invalid argument value: '{arg}' is out of range. Must be float >= 0."
            raise argparse.ArgumentTypeError(msg)
        return arg_float


class PositiveFloatRange:
    """Validate argument is a nondecreasing, nonzero float range.

    Float ranges are expressed as two floats separated by a hyphen, for example
    `0.1-1.0`.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid float range.

    """

    METAVAR = "(hyphen separated float range e.g. '0.25-0.5')"

    @staticmethod
    def type_parser(arg: str | tuple[float, float] | list[float]) -> tuple[float, float]:
        """Validate argument is a valid range of positive floats.

        Args:
            arg (str): argument to validate

        Returns:
            tuple[float,float]: validated range

        """
        try:
            if isinstance(arg, (tuple, list)):
                invalid_value = len(arg) != 2 or any(
                    isinstance(value, bool) or not isinstance(value, (int, float)) for value in arg
                )
                if invalid_value:
                    msg = f"invalid range: '{arg}' is not a valid range. Must be start-end. Ex: 0.1-1.0"
                    raise argparse.ArgumentTypeError(msg)
                start, end = map(float, arg)
            else:
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

        except (AttributeError, ValueError):
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
    def type_parser(arg: str | float) -> float:
        """Validate argument is a float value between zero and one.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not in range.

        Returns:
            float: validated float value

        """
        if isinstance(arg, bool) or not isinstance(arg, (str, int, float)):
            msg = f"invalid value: '{arg}' is not a float or int."
            raise argparse.ArgumentTypeError(msg)
        try:
            arg_float = float(arg)
        except ValueError:
            msg = f"invalid value: '{arg}' is not a float or int."
            raise argparse.ArgumentTypeError(msg) from None

        if 0 <= arg_float <= 1:
            return arg_float
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
    def type_parser(arg: str | float) -> float:
        """Validate argument is a positive float.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not in range.

        Returns:
            float: validated float value

        """
        if isinstance(arg, bool) or not isinstance(arg, (str, int, float)):
            msg = f"invalid value: '{arg}' is not a float or int."
            raise argparse.ArgumentTypeError(msg)
        try:
            arg_float = float(arg)
        except ValueError:
            msg = f"invalid value: '{arg}' is not a float or int."
            raise argparse.ArgumentTypeError(msg) from None

        if 0 < arg_float <= 1:
            return arg_float
        msg = f"invalid value: '{arg}' must be 0 < n <=1. Example: 0.5"
        raise argparse.ArgumentTypeError(msg)


class GradientDirection:
    """Validate argument is a valid gradient direction.

    Raises:
        argparse.ArgumentTypeError: Argument value is not a valid gradient direction.

    """

    METAVAR = "(diagonal, horizontal, vertical, radial)"

    @staticmethod
    def type_parser(arg: str | Gradient.Direction) -> Gradient.Direction:
        """Validate argument is a valid gradient direction.

        Args:
            arg (str): argument to validate

        Returns:
            Gradient.Direction: validated gradient direction

        Raises:
            argparse.ArgumentTypeError: Argument value is not a valid gradient direction.

        """
        if isinstance(arg, Gradient.Direction):
            return arg
        direction_map = {
            "horizontal": Gradient.Direction.HORIZONTAL,
            "vertical": Gradient.Direction.VERTICAL,
            "diagonal": Gradient.Direction.DIAGONAL,
            "radial": Gradient.Direction.RADIAL,
        }
        if isinstance(arg, str) and arg.lower() in direction_map:
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
    def type_parser(arg: str | int | Color) -> Color:
        """Validate argument is a valid color value.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Color value is not in range.

        Returns:
            Color : validated color value

        """
        if isinstance(arg, Color):
            return arg
        if isinstance(arg, bool) or not isinstance(arg, (str, int)):
            msg = (
                f"invalid color value: '{arg}' is not a valid XTerm or RGB color."
                " Must be in range 0-255 or 000000-FFFFFF."
            )
            raise argparse.ArgumentTypeError(msg)
        try:
            return Color(int(arg)) if isinstance(arg, int) or len(arg) <= 3 else Color(arg)
        except (TypeError, ValueError):
            msg = (
                f"invalid color value: '{arg}' is not a valid XTerm or RGB color."
                " Must be in range 0-255 or 000000-FFFFFF."
            )
            raise argparse.ArgumentTypeError(msg) from None


class Symbol:
    """Validate argument is a single printable character.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid symbol.

    """

    METAVAR = "(ASCII/UTF-8 character)"

    @staticmethod
    def type_parser(arg: str) -> str:
        """Validate argument is a single printable character.

        Args:
            arg (str): argument to validate

        Returns:
            str: validated symbol

        """
        if isinstance(arg, str) and len(arg) == 1 and arg.isprintable():
            return arg
        msg = f"invalid symbol: '{arg}' is not a valid symbol. Must be a single ASCII/UTF-8 character."
        raise argparse.ArgumentTypeError(msg)


class CanvasDimension:
    """Validate argument is a nonnegative integer or `-1`.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid canvas dimension.

    """

    METAVAR = "int >= -1"

    @staticmethod
    def type_parser(arg: str | int) -> int:
        """Validate argument is a nonnegative integer or `-1`.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not a valid canvas dimension.

        Returns:
            int: validated canvas dimension

        """
        if isinstance(arg, int) and not isinstance(arg, bool) and arg >= -1:
            return arg
        if isinstance(arg, str) and (arg.isdigit() or arg == "-1"):
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
    def type_parser(arg: str | int) -> int:
        """Validate argument is a valid terminal dimension.

        Args:
            arg (str): argument to validate

        Returns:
            int: validated terminal dimension

        """
        if isinstance(arg, bool) or not isinstance(arg, (str, int)):
            msg = f"invalid terminal dimensions: '{arg}' is not a valid terminal dimension. Must be >= 0."
            raise argparse.ArgumentTypeError(msg)
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
    def type_parser(arg: str | typing.Callable) -> typing.Callable:
        """Validate argument is a valid easing function.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Ease value is not a valid easing function.

        Returns:
            typing.Callable: The validated easing function.

        """
        if callable(arg):
            return arg
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
        except (AttributeError, KeyError):
            msg = f"invalid ease value: '{arg}' is not a valid ease."
            raise argparse.ArgumentTypeError(msg) from None


class EasingStep:
    """Validate argument is a valid easing step size value.

    Raises:
        argparse.ArgumentTypeError: Value is not a valid easing step size.

    """

    METAVAR = "0 < float(n) <= 1"

    @staticmethod
    def type_parser(arg: str | float) -> float:
        """Validate argument is a valid easing step size value.

        Args:
            arg (str): argument to validate

        Raises:
            argparse.ArgumentTypeError: Value is not a valid easing step size.

        Returns:
            float: validated easing step size value

        """
        if isinstance(arg, bool) or not isinstance(arg, (str, int, float)):
            msg = f"invalid value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg)
        try:
            f = float(arg)
        except ValueError:
            msg = f"invalid value: '{arg}' is not a valid float."
            raise argparse.ArgumentTypeError(msg) from None

        if 0 < f <= 1:
            return f
        msg = f"invalid value: '{arg}' is not a float > 0 and <= 1. Example: 0.5"
        raise argparse.ArgumentTypeError(msg)
