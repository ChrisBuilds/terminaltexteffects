"""Classes for storing and manipulating character graphics.

Classes:
    Color: Represents a color in the RGB color space. Can be initialized with an XTerm-256 color code or an RGB hex
        color string.
    ColorPair: Represents a pair of colors to specify a character's foreground and background colors.
    Gradient: A list of `Color` objects transitioning from one color stop to another. Supports various gradient
        directions.
"""

from __future__ import annotations

import math
import random
import typing
from dataclasses import dataclass, field
from enum import Enum, auto

from terminaltexteffects.utils import ansitools, colorterm, geometry, hexterm

if typing.TYPE_CHECKING:
    from collections.abc import Iterator


@dataclass(frozen=True, init=False, repr=False, eq=False)
class Color:
    """Represents a color in the RGB color space.

    The color can be initialized with an XTerm-256 color code or an RGB hex color string. Can be printed
    to display the color code and appearance as a color block. RGB specifications are normalized to lowercase without
    a leading hash. Equality and hashing preserve the normalized specification: equivalent RGB spellings compare
    equal, while XTerm indices remain distinct from RGB specifications and from other indices. Instances are immutable.

    Attributes:
        color_arg (int | str): The color value as an XTerm-256 color code or an RGB hex color string.
        xterm_color (int | None): The XTerm-256 color code. None if the color is an RGB hex color string.
        rgb_color (str): The RGB hex color string.

    Properties:
        rgb_ints (tuple[int, int, int]): Returns the RGB values as a tuple of integers.

    Raises:
        ValueError: If the color value is not a valid XTerm-256 color code or an RGB hex color string.

    """

    color_arg: int | str
    xterm_color: int | None
    rgb_color: str
    _rgb_ints: tuple[int, int, int] = field(init=False, repr=False, compare=False)

    def __init__(self, color_value: int | str) -> None:
        """Initialize a Color object.

        Args:
            color_value (int | str): The color value as an XTerm-256 color code or an RGB hex color string.
                Example: 255 or 'ffffff' or '#ffffff'

        Raises:
            ValueError: If the color value is not a valid XTerm-256 color code or an RGB hex color string.

        """
        if not hexterm.is_valid_color(color_value):
            msg = (
                "Invalid color value. Color must be an XTerm-256 color code or an RGB hex color string. "
                "Example: 255 or 'ffffff' or '#ffffff'"
            )
            raise ValueError(
                msg,
            )
        if isinstance(color_value, str):
            color_value = color_value.removeprefix("#").lower()
        object.__setattr__(self, "color_arg", color_value)
        if isinstance(color_value, int):
            object.__setattr__(self, "xterm_color", color_value)
            object.__setattr__(self, "rgb_color", hexterm.xterm_to_hex(color_value))
        else:
            object.__setattr__(self, "rgb_color", color_value)
            object.__setattr__(self, "xterm_color", None)
        object.__setattr__(self, "_rgb_ints", colorterm._hex_to_int(self.rgb_color))

    @classmethod
    def _from_rgb_ints(cls, rgb_ints: tuple[int, int, int]) -> Color:
        """Create an RGB `Color` from channels already validated by internal calculations."""
        color = cls.__new__(cls)
        rgb_color = f"{rgb_ints[0]:02x}{rgb_ints[1]:02x}{rgb_ints[2]:02x}"
        object.__setattr__(color, "color_arg", rgb_color)
        object.__setattr__(color, "xterm_color", None)
        object.__setattr__(color, "rgb_color", rgb_color)
        object.__setattr__(color, "_rgb_ints", rgb_ints)
        return color

    @property
    def rgb_ints(self) -> tuple[int, int, int]:
        """Returns the RGB values as a tuple of integers.

        Returns:
            tuple[int, int, int]: The RGB values as a tuple of integers.

        """
        return self._rgb_ints

    def __repr__(self) -> str:
        """Return a constructor-compatible representation of the `Color`."""
        return f"Color({self.color_arg!r})"

    def __str__(self) -> str:
        """Return a string representation of the Color object."""
        color_block = f"{colorterm.fg(self.rgb_color)}█████{ansitools.reset_all()}"
        xterm_display = f" | XTerm Color: {self.xterm_color}" if self.xterm_color is not None else ""
        return (
            f"Color Code: {self.rgb_color}{xterm_display}"
            f"\nColor Appearance: {color_block}"
        )

    def __eq__(self, other: object) -> bool:
        """Return whether this color has the same normalized specification as another `Color`.

        Returns `NotImplemented` when `other` is not a `Color`.
        """
        if not isinstance(other, Color):
            return NotImplemented
        return self.color_arg == other.color_arg

    def __ne__(self, other: object) -> bool:
        """Return whether this color is not equal to another `Color`.

        Returns `NotImplemented` when `other` is not a `Color`.
        """
        if not isinstance(other, Color):
            return NotImplemented
        return self.color_arg != other.color_arg

    def __hash__(self) -> int:
        """Return the hash of this color's normalized specification."""
        return hash(self.color_arg)

    def __iter__(self) -> Iterator[Color]:
        """Return an iterator yielding this `Color` instance once."""
        return iter((self,))


@dataclass(frozen=True, init=False)
class ColorPair:
    """Represents a pair of colors to specify a character's foreground and background colors.

    `fg` and `bg` are the immutable fields. On init, `Color` instances are preserved, non-`Color` non-`None` values
    are converted to `Color`, and `None` values remain unset.

    Attributes:
        fg (Color | None): The foreground color. None if no foreground color is specified.
        bg (Color | None): The background color. None if no background color is specified.

    """

    fg: Color | None
    bg: Color | None
    __match_args__: typing.ClassVar[tuple[str, str]] = ("fg", "bg")

    def __init__(
        self,
        fg: Color | str | int | None = None,
        bg: Color | str | int | None = None,
    ) -> None:
        """Initialize and normalize the foreground and background values.

        `Color` instances are preserved, non-`Color` non-`None` values are converted to
        `Color`, and `None` values remain unset.
        """
        object.__setattr__(self, "fg", Color(fg) if fg is not None and not isinstance(fg, Color) else fg)
        object.__setattr__(self, "bg", Color(bg) if bg is not None and not isinstance(bg, Color) else bg)

    def __str__(self) -> str:
        """Return a string representation of the ColorPair object."""
        color_block = (
            f"{colorterm.fg(self.fg.rgb_color) if self.fg else ''}"
            f"{colorterm.bg(self.bg.rgb_color) if self.bg else ''}####{ansitools.reset_all()}"
        )
        return (
            f"Foreground Color Code: {self.fg.rgb_color if self.fg else ''}"
            f"{f' | Foreground XTerm Color: {self.fg.xterm_color}' if self.fg and self.fg.xterm_color is not None else ''}\n"  # noqa: E501
            f"Background Color Code: {self.bg.rgb_color if self.bg else ''}"
            f"{f' | Background XTerm Color: {self.bg.xterm_color}' if self.bg and self.bg.xterm_color is not None else ''}"  # noqa: E501
            f"\nColor Appearance: {color_block}"
        )


def _interpolate_rgb(
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    factor: float,
) -> tuple[int, int, int]:
    """Interpolate RGB channels using nearest, ties-to-even rounding."""
    return (
        round(start[0] + ((end[0] - start[0]) * factor)),
        round(start[1] + ((end[1] - start[1]) * factor)),
        round(start[2] + ((end[2] - start[2]) * factor)),
    )


class Gradient:
    """A Gradient is a list of `Color` objects transitioning from one color stop to another.

    The gradient color list is calculated using linear interpolation based on the provided start and end colors
    and the number of steps. Gradients can be iterated over to get the next color in the gradient color list.
    If there is only one color in the stops list, the gradient contains that color once because there are no
    transitions to generate.

    If multiple steps are given, the gradient between pairs of colors will be equal to the number of steps for the pair
    based on the order of stops and steps.

    Ex: stops = ("ffffff", "aaaaaa", "000000"), steps = (6, 3)

    "fffffff" -> (6 steps) -> "aaaaaa" -> (3 steps) -> "000000"

    A step count is the number of transitions between a pair of adjacent stops. Total number of colors in a
    multi-stop gradient spectrum is the sum of the effective step counts plus 1. A single integer applies to every
    transition. A tuple assigns counts in order; if it contains fewer values than transitions, its last value is
    repeated. When transitions exist, a tuple cannot contain more values than there are transitions. For a single-stop
    gradient, step values are validated but tuple cardinality does not change the one-color spectrum.

    Attributes:
        spectrum (list[Color]): The generated `Color` objects. Multi-stop gradients contain
            `sum(effective_steps) + 1` colors; single-stop gradients contain one color.

    """

    class Direction(Enum):
        """Enum for specifying the direction of the gradient."""

        VERTICAL = auto()
        HORIZONTAL = auto()
        RADIAL = auto()
        DIAGONAL = auto()

    def __init__(self, *stops: Color, steps: tuple[int, ...] | int = 1, loop: bool = False) -> None:
        """Initialize a Gradient object.

        Args:
            stops (Color): One or more `Color` objects representing the color stops.
            steps (int | tuple[int, ...], optional): Number of transitions or a tuple of transition counts for
                generating the spectrum. A single value is repeated for every adjacent stop pair. Defaults to 1.
            loop (bool, optional): Loop the gradient. This causes the final gradient color to transition back to the
                first gradient color. Defaults to False.

        Raises:
            TypeError: If any stop is not a `Color`.
            ValueError: If no color stops are provided or any step count is invalid.

        Attributes:
            _stops (tuple[Color]): Tuple of Color objects representing the color stops.
            _steps (int | tuple[int, ...]): Number of steps or a tuple of step values for generating the spectrum.
            _loop (bool): Loop the gradient. This causes the final gradient color to transition back to the
                first gradient color.
            spectrum (list[Color]): List of generated `Color` objects representing the spectrum.

        Returns:
            None

        """
        self._stops = stops
        if len(self._stops) < 1:
            msg = "At least one stop must be provided."
            raise ValueError(msg)
        if any(not isinstance(stop, Color) for stop in self._stops):
            msg = "Stops must be Color instances."
            raise TypeError(msg)
        step_values = self._validate_steps(steps)
        self._steps = steps
        self._loop = loop
        transition_count = len(self._stops) if self._loop and len(self._stops) > 1 else len(self._stops) - 1
        if transition_count and len(step_values) > transition_count:
            msg = "A steps tuple cannot contain more values than the gradient has transitions."
            raise ValueError(msg)
        effective_steps = step_values + (step_values[-1],) * (transition_count - len(step_values))
        self.spectrum: list[Color] = self._generate(effective_steps)

    @staticmethod
    def _validate_steps(steps: int | tuple[int, ...]) -> tuple[int, ...]:
        """Validate and return gradient transition counts as a tuple."""
        step_values = (steps,) if isinstance(steps, int) and not isinstance(steps, bool) else steps
        if not isinstance(step_values, tuple) or not step_values:
            msg = "Steps must be a positive integer or a non-empty tuple of positive integers."
            raise ValueError(msg)
        if any(isinstance(step, bool) or not isinstance(step, int) or step < 1 for step in step_values):
            msg = "Steps must be a positive integer or a non-empty tuple of positive integers."
            raise ValueError(msg)
        return step_values

    def get_color_at_fraction(self, fraction: float) -> Color:
        """Return the precomputed spectrum color corresponding to a normalized fraction.

        The fraction is matched to the nearest precomputed spectrum color from start
        to end. Ties use Python's round-to-even behavior. A fraction of `0` returns
        the first color and `1` returns the final color.

        Args:
            fraction (float): The fraction of the gradient to get the color for.

        Returns:
            Color: The color at the fraction of the gradient.

        Raises:
            TypeError: If `fraction` is not an integer or float.
            ValueError: If `fraction` is not finite or outside the inclusive range from `0` to `1`.

        """
        if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
            msg = "Fraction must be an integer or float."
            raise TypeError(msg)
        if not math.isfinite(fraction):
            msg = "Fraction must be finite."
            raise ValueError(msg)
        if fraction < 0 or fraction > 1:
            msg = "Fraction must be 0 <= fraction <= 1."
            raise ValueError(msg)
        spectrum_index = round(fraction * (len(self.spectrum) - 1))
        return self.spectrum[spectrum_index]

    def _generate(self, steps: tuple[int, ...]) -> list[Color]:
        """Calculate a gradient of colors between two colors using linear interpolation.

        If there is only one color in the stops tuple, the gradient contains that color once.

        If multiple steps are given, the gradient between pairs of colors will be equal to the number of steps
        for the pair based on the order of stops and steps.

        Ex: stops = ("ffffff", "aaaaaa", "000000"), steps = (6, 3)
        Distance from "ffffff" to "aaaaaa" = 6 steps (7 colors including start and end)
        Distance from "aaaaaa" to "000000" = 3 steps (4 colors including start and end)
        Total colors in the gradient spectrum = 10 ("aaaaaa" is not repeated when transitioning from
        "ffffff" to "aaaaaa" and from "aaaaaa" to "000000")

        A step count is the number of transitions between a pair. Total number of colors in a multi-stop gradient
        spectrum is `sum(steps) + 1`.

        Returns:
            list[Color]: Generated colors. The first and last colors are the start and end stops, respectively.

        """
        if len(self._stops) == 1:
            return [self._stops[0]]
        generation_stops = (*self._stops, self._stops[0]) if self._loop else self._stops
        spectrum = [generation_stops[0]]
        color_pairs = zip(generation_stops, generation_stops[1:])
        for (start, end), step_count in zip(color_pairs, steps):
            start_color_ints = start.rgb_ints
            end_color_ints = end.rgb_ints
            for i in range(1, step_count):
                fraction = i / step_count
                spectrum.append(Color._from_rgb_ints(_interpolate_rgb(start_color_ints, end_color_ints, fraction)))
            spectrum.append(end)
        return spectrum

    def build_coordinate_color_mapping(
        self,
        min_row: int,
        max_row: int,
        min_column: int,
        max_column: int,
        direction: Gradient.Direction,
    ) -> dict[geometry.Coord, Color]:
        """Build a mapping of coordinates to colors based on the gradient and a direction.

        For example, a vertical gradient will have the same color for each character in a row. When applied across all
        characters in the canvas, the gradient will be visible as a vertical gradient. The mapping respects the
        provided row and column bounds for every direction. Vertical, horizontal, and diagonal mappings assign the
        first and final gradient colors to the endpoints of each non-degenerate directional span. Radial mappings
        assign the first color at the center and the final color at the corners. A mapping containing only one
        coordinate receives the first color in every direction.

        Args:
            min_row (int): The minimum row value. Must be greater than 0 and less than or equal to max_row.
            max_row (int): The maximum row value. Must be greater than 0 and greater than or equal to min_row.
            min_column (int): The minimum column value. Must be greater than 0 and less than or equal to max_column.
            max_column (int): The maximum column value. Must be greater than 0 and greater than or equal to min_column.
            direction (Gradient.Direction): The direction of the gradient.

        Returns:
            dict[geometry.Coord, Color]: A mapping of coordinates to `Color` objects.

        Raises:
            TypeError: If `direction` is not a `Gradient.Direction` or any coordinate bound is not a non-boolean
                integer.
            ValueError: If any coordinate bound is less than one or a minimum bound exceeds its maximum.

        """
        if not isinstance(direction, Gradient.Direction):
            msg = "direction must be a Gradient.Direction."
            raise TypeError(msg)
        bounds = (min_row, max_row, min_column, max_column)
        if any(isinstance(value, bool) or not isinstance(value, int) for value in bounds):
            msg = "Coordinate bounds must be non-boolean integers."
            raise TypeError(msg)
        if any(value < 1 for value in bounds):
            msg = "Coordinate bounds must be greater than 0."
            raise ValueError(msg)
        if min_row > max_row or min_column > max_column:
            msg = "min_row and min_column must be less than or equal to max_row and max_column."
            raise ValueError(msg)
        row_span = max_row - min_row
        column_span = max_column - min_column
        gradient_mapping: dict[geometry.Coord, Color] = {}
        if direction == Gradient.Direction.VERTICAL:
            for row_value in range(min_row, max_row + 1):
                fraction = (row_value - min_row) / row_span if row_span else 0
                color = self.get_color_at_fraction(fraction)
                for column_value in range(min_column, max_column + 1):
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color
        elif direction == Gradient.Direction.HORIZONTAL:
            for column_value in range(min_column, max_column + 1):
                fraction = (column_value - min_column) / column_span if column_span else 0
                color = self.get_color_at_fraction(fraction)
                for row_value in range(min_row, max_row + 1):
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color
        elif direction == Gradient.Direction.RADIAL:
            for row_value in range(min_row, max_row + 1):
                for column_value in range(min_column, max_column + 1):
                    distance_from_center = geometry.find_normalized_distance_from_center(
                        min_row,
                        max_row,
                        min_column,
                        max_column,
                        geometry.Coord(column_value, row_value),
                    )
                    color = self.get_color_at_fraction(distance_from_center)
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color
        elif direction == Gradient.Direction.DIAGONAL:
            diagonal_span = (row_span * geometry.TERMINAL_ROW_SCALE) + column_span
            for row_value in range(min_row, max_row + 1):
                for column_value in range(min_column, max_column + 1):
                    fraction = (
                        ((row_value - min_row) * geometry.TERMINAL_ROW_SCALE) + (column_value - min_column)
                    )
                    fraction = fraction / diagonal_span if diagonal_span else 0
                    color = self.get_color_at_fraction(fraction)
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color

        return gradient_mapping

    def __iter__(self) -> Iterator[Color]:
        """Return an iterator over the Gradient object."""
        yield from self.spectrum

    def __len__(self) -> int:
        """Return the length of the Gradient object."""
        return len(self.spectrum)

    @typing.overload
    def __getitem__(self, index: int) -> Color: ...

    @typing.overload
    def __getitem__(self, index: slice) -> list[Color]: ...

    def __getitem__(self, index: int | slice) -> Color | list[Color]:
        """Return the color at the given index or a list of colors based on the slice."""
        return self.spectrum[index]

    def __str__(self) -> str:
        """Return a string representation of the Gradient object."""
        color_blocks = [f"{colorterm.fg(color.rgb_color)}█{ansitools.reset_all()}" for color in self.spectrum]
        return f"Gradient: Stops({', '.join(c.rgb_color for c in self._stops)}), Steps({self._steps})\n" + "".join(
            color_blocks,
        )


def random_color() -> Color:
    """Return a random `Color` created from a six-digit RGB hex value.

    Returns:
        Color: A random color.

    """
    return Color(f"{random.randint(0, 0xFFFFFF):06x}")


def shift_color_towards(color: Color, target_color: Color, factor: float) -> Color:
    """Shift one color towards another by a given factor.

    A factor of `0` returns the original color and a factor of `1` returns the
    target color. The factor must be between `0` and `1`, inclusive.

    Args:
        color (Color): The original color.
        target_color (Color): The target color to shift towards.
        factor (float): Interpolation factor used to shift the color.

    Returns:
        Color: The resulting color after shifting.

    Raises:
        ValueError: If `factor` is outside the inclusive range from `0` to `1`.

    """
    if not 0 <= factor <= 1:
        msg = "Factor must be between 0 and 1, inclusive."
        raise ValueError(msg)

    return Color._from_rgb_ints(_interpolate_rgb(color.rgb_ints, target_color.rgb_ints, factor))
