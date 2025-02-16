"""Classes for storing and manipulating character graphics.

Classes:
    Color: Represents a color in the RGB color space. Can be initialized with an XTerm-256 color code or an RGB hex
        color string.
    ColorPair: Represents a pair of colors to specify a character's foreground and background colors.
    Gradient: A list of RGB hex color strings transitioning from one color to another. Supports various gradient
        directions.
"""

from __future__ import annotations

import itertools
import random
import typing
from dataclasses import InitVar, dataclass, field
from enum import Enum, auto

from terminaltexteffects.utils import ansitools, colorterm, geometry, hexterm

if typing.TYPE_CHECKING:
    from collections.abc import Iterator


class Color:
    """Represents a color in the RGB color space.

    The color can be initialized with an XTerm-256 color code or an RGB hex color string. Can be printed
    to display the color code and appearance as a color block.

    Attributes:
        color_arg (int | str): The color value as an XTerm-256 color code or an RGB hex color string.
        xterm_color (int | None): The XTerm-256 color code. None if the color is an RGB hex color string.
        rgb_color (str): The RGB hex color string.

    Properties:
        rgb_ints (tuple[int, int, int]): Returns the RGB values as a tuple of integers.

    Raises:
        ValueError: If the color value is not a valid XTerm-256 color code or an RGB hex color string.

    """

    def __init__(self, color_value: int | str) -> None:
        """Initialize a Color object.

        Args:
            color_value (int | str): The color value as an XTerm-256 color code or an RGB hex color string.
                Example: 255 or 'ffffff' or '#ffffff'

        Raises:
            ValueError: If the color value is not a valid XTerm-256 color code or an RGB hex color string.

        """
        if isinstance(color_value, str):
            color_value = color_value.strip("#")
        self.color_arg = color_value
        self.xterm_color: int | None = None
        if hexterm.is_valid_color(color_value):
            if isinstance(color_value, int):
                self.xterm_color = color_value
                self.rgb_color = hexterm.xterm_to_hex(color_value)
            else:
                self.rgb_color = color_value
                self.xterm_color = None
        else:
            msg = (
                "Invalid color value. Color must be an XTerm-256 color code or an RGB hex color string. "
                "Example: 255 or 'ffffff' or '#ffffff'"
            )
            raise ValueError(
                msg,
            )

    @property
    def rgb_ints(self) -> tuple[int, int, int]:
        """Returns the RGB values as a tuple of integers.

        Returns:
            tuple[int, int, int]: The RGB values as a tuple of integers.

        """
        return colorterm._hex_to_int(self.rgb_color)

    def __repr__(self) -> str:
        """Return a string representation of the Color object."""
        return f"Color('{self.color_arg}')"

    def __str__(self) -> str:
        """Return a string representation of the Color object."""
        color_block = f"{colorterm.fg(self.rgb_color)}█████{ansitools.reset_all()}"
        return (
            f"Color Code: {self.rgb_color}{f' | XTerm Color: {self.xterm_color}' if self.xterm_color else ''}"
            f"\nColor Appearance: {color_block}"
        )

    def __eq__(self, other: object) -> bool:
        """Check if two Color objects are equal."""
        if not isinstance(other, Color):
            return NotImplemented
        return self.color_arg == other.color_arg

    def __ne__(self, other: object) -> bool:
        """Check if two Color objects are not equal."""
        if not isinstance(other, Color):
            return NotImplemented
        return self.color_arg != other.color_arg

    def __hash__(self) -> int:
        """Return the hash value of the Color object."""
        return hash(self.color_arg)

    def __iter__(self) -> Iterator[Color]:
        """Return an iterator over the Color object."""
        return iter((self,))


@dataclass()
class ColorPair:
    """Represents a pair of colors to specify a character's foreground and background colors.

    On init, if fg or bg is not a Color object, create a Color object with the value.

    Attributes:
        fg_color (Color | None): The foreground color. None if no foreground color is specified.
        bg_color (Color | None): The background color. None if no background color is specified.
        fg (InitVar[Color | str | int | None]): The initial foreground color value.
        bg (InitVar[Color | str | int | None]): The initial background color value.

    """

    fg_color: Color | None = field(init=False, default=None)
    bg_color: Color | None = field(init=False, default=None)
    fg: InitVar[Color | str | int | None] = None
    bg: InitVar[Color | str | int | None] = None

    def __post_init__(self, init_fg_color: Color | str | int | None, init_bg_color: Color | str | int | None) -> None:
        """If either fg or bg is not a Color object, create a Color object with the value."""
        if init_fg_color is not None and not isinstance(init_fg_color, Color):
            self.fg_color = Color(init_fg_color)
        else:
            self.fg_color = init_fg_color

        if init_bg_color is not None and not isinstance(init_bg_color, Color):
            self.bg_color = Color(init_bg_color)
        else:
            self.bg_color = init_bg_color

    def __str__(self) -> str:
        """Return a string representation of the ColorPair object."""
        color_block = (
            f"{colorterm.fg(self.fg_color.rgb_color) if self.fg_color else ''}"
            f"{colorterm.bg(self.bg_color.rgb_color) if self.bg_color else ''}####{ansitools.reset_all()}"
        )
        return (
            f"Foreground Color Code: {self.fg_color.rgb_color if self.fg_color else ''}"
            f"{f' | Foreground XTerm Color: {self.fg_color.xterm_color}' if self.fg_color and self.fg_color.xterm_color else ''}\n"
            f"Background Color Code: {self.bg_color.rgb_color if self.bg_color else ''}"
            f"{f' | Background XTerm Color: {self.bg_color.xterm_color}' if self.bg_color and self.bg_color.xterm_color else ''}"
            f"\nColor Appearance: {color_block}"
        )


class Gradient:
    """A Gradient is a list of RGB hex color strings transitioning from one color to another.

    The gradient color list is calculated using linear interpolation based on the provided start and end colors
    and the number of steps. Gradients can be iterated over to get the next color in the gradient color list.
    If there is only one color in the stops list, the gradient will be a list of the same color.

    If multiple steps are given, the gradient between pairs of colors will be equal to the number of steps for the pair
    based on the order of stops and steps.

    Ex: stops = ("ffffff", "aaaaaa", "000000"), steps = (6, 3)

    "fffffff" -> (6 steps) -> "aaaaaa" -> (3 steps) -> "000000"

    The step count includes the stop for each pair. Total number of colors in the resulting gradient spectrum
    is the sum of the steps between each pair of stops plus 1.

    Attributes:
        spectrum (list[str]): List (length=sum(steps) + 1) of RGB hex color strings

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
            stops (Color): One ore more variables of type Color representing the color stops.
            steps (int | tuple[int, ...], optional): Number of steps or a tuple of step values for generating the
                spectrum. Defaults to 1.
            loop (bool, optional): Loop the gradient. This causes the final gradient color to transition back to the
                first gradient color. Defaults to False.

        Raises:
            ValueError: If no color stops are provided.

        Attributes:
            _stops (tuple[Color]): Tuple of Color objects representing the color stops.
            _steps (int | tuple[int, ...]): Number of steps or a tuple of step values for generating the spectrum.
            _loop (bool): Loop the gradient. This causes the final gradient color to transition back to the
                first gradient color.
            spectrum (list[str]): List of strings representing the generated spectrum.
            _index (int): Current index of the spectrum.

        Returns:
            None

        """
        self._stops = stops
        if len(self._stops) < 1:
            msg = "At least one stop must be provided."
            raise ValueError(msg)
        self._steps = steps
        self._loop = loop
        self.spectrum: list[Color] = self._generate(self._steps)
        self._index: int = 0

    def get_color_at_fraction(self, fraction: float) -> Color:
        """Return the color at a fraction of the gradient.

        Args:
            fraction (float): The fraction of the gradient to get the color for.

        Returns:
            Color: The color at the fraction of the gradient.

        """
        if fraction < 0 or fraction > 1:
            msg = "Fraction must be 0 <= fraction <= 1."
            raise ValueError(msg)
        for i in range(1, len(self.spectrum) + 1):
            if fraction <= i / len(self.spectrum):
                return self.spectrum[i - 1]
        return self.spectrum[-1]

    def _generate(self, steps: int | tuple[int, ...]) -> list[Color]:
        """Calculate a gradient of colors between two colors using linear interpolation.

        If there is only one color in the stops tuple, the gradient will be a list of the same color.

        If multiple steps are given, the gradient between pairs of colors will be equal to the number of steps
        for the pair based on the order of stops and steps.

        Ex: stops = ("ffffff", "aaaaaa", "000000"), steps = (6, 3)
        Distance from "ffffff" to "aaaaaa" = 6 steps (7 colors including start and end)
        Distance from "aaaaaa" to "000000" = 3 steps (4 colors including start and end)
        Total colors in the gradient spectrum = 10 ("aaaaaa" is not repeated when transitioning from
        "ffffff" to "aaaaaa" and from "aaaaaa" to "000000")


        The step count includes the stop for each pair. Total number of colors in the resulting gradient spectrum:
        sum(steps) + 1

        Returns:
            list[str]: List (length=sum(steps) + 1) of RGB hex color strings. The first and last colors are
                the start and end stops, respectively.

        """
        if isinstance(steps, int):
            steps = (steps,)
            for step in steps:
                if step < 1:
                    msg = "Steps must be greater than 0."
                    raise ValueError(msg)
        spectrum: list[Color] = []
        if len(self._stops) == 1:
            color = self._stops[0]
            spectrum.extend(color for _ in range(steps[0]))
            return spectrum
        if self._loop:
            self._stops = (*self._stops, self._stops[0])
        a, b = itertools.tee(self._stops)
        next(b, None)
        color_pairs = list(zip(a, b))
        steps = steps[: len(color_pairs)]
        if len(steps) < len(color_pairs):
            steps = steps + (steps[-1],) * (len(color_pairs) - len(steps))
        color_pair: tuple[Color, Color]
        for color_pair, step_count in zip(color_pairs, steps):
            if step_count < 1:
                msg = f"Invalid steps: {step_count} | Steps must be greater than 0."
                raise ValueError(msg)
            start, end = color_pair
            start_color_ints = start.rgb_ints
            end_color_ints = end.rgb_ints
            # Initialize an empty list to store the gradient colors
            gradient_colors: list[Color] = []
            # Calculate the color deltas for each RGB value
            red_delta = (end_color_ints[0] - start_color_ints[0]) // step_count
            green_delta = (end_color_ints[1] - start_color_ints[1]) // step_count
            blue_delta = (end_color_ints[2] - start_color_ints[2]) // step_count
            # Calculate the intermediate colors and add them to the gradient colors list
            range_start = int(len(spectrum) > 0)  # if this is the first pair, add the start color to the spectrum
            for i in range(range_start, max(step_count, 0)):
                red = start_color_ints[0] + (red_delta * i)
                green = start_color_ints[1] + (green_delta * i)
                blue = start_color_ints[2] + (blue_delta * i)

                # Ensure that the RGB values are within the valid range of 0-255
                red = max(0, min(red, 255))
                green = max(0, min(green, 255))
                blue = max(0, min(blue, 255))

                # Convert the RGB values to a hex color string and add it to the gradient colors list
                gradient_colors.append(Color(f"{red:02x}{green:02x}{blue:02x}"))
            # Add the end color to the gradient colors list
            gradient_colors.append(end)
            spectrum.extend(gradient_colors)
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

        For example, a vertical gradient will have the same color for each column in a row. When applied across all
        characters in the canvas, the gradient will be visible as a vertical gradient.

        Args:
            min_row (int): The minimum row value. Must be greater than 0 and less than or equal to max_row.
            max_row (int): The maximum row value. Must be greater than 0 and greater than or equal to min_row.
            min_column (int): The minimum column value. Must be greater than 0 and less than or equal to max_column.
            max_column (int): The maximum column value. Must be greater than 0 and greater than or equal to min_column.
            direction (Gradient.Direction): The direction of the gradient.

        Returns:
            dict[Coord, str]: A mapping of coordinates to colors.

        """
        if any(value < 1 for value in (max_row, max_column, min_row, min_column)):
            msg = "max_row and max_column must be greater than 0."
            raise ValueError(msg)
        if min_row > max_row or min_column > max_column:
            msg = "min_row and min_column must be less than or equal to max_row and max_column."
            raise ValueError(msg)
        row_offset = min_row - 1
        column_offset = min_column - 1
        gradient_mapping: dict[geometry.Coord, Color] = {}
        if direction == Gradient.Direction.VERTICAL:
            for row_value in range(min_row, max_row + 1):
                fraction = (row_value - row_offset) / (max_row - row_offset)
                color = self.get_color_at_fraction(fraction)
                for column_value in range(min_column, max_column + 1):
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color
        elif direction == Gradient.Direction.HORIZONTAL:
            for column_value in range(min_column, max_column + 1):
                fraction = (column_value - column_offset) / (max_column - column_offset)
                color = self.get_color_at_fraction(fraction)
                for row_value in range(1, max_row + 1):
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
            for row_value in range(min_row, max_row + 1):
                for column_value in range(min_column, max_column + 1):
                    fraction = (((row_value - row_offset) * 2) + (column_value - column_offset)) / (
                        ((max_row - row_offset) * 2) + (max_column - column_offset)
                    )
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
    """Return a random color in the range 000000 -> ffffff.

    Returns:
        Color: A random color in the range 000000 -> ffffff.

    """
    return Color(hex(random.randint(0, 0xFFFFFF))[2:].zfill(6))


def shift_color_towards(color: Color, target_color: Color, factor: float) -> Color:
    """Shift one color towards another by a given factor.

    Args:
        color (Color): The original color.
        target_color (Color): The target color to shift towards.
        factor (float): The factor by which to shift the color (0.0 to 1.0).

    Returns:
        Color: The resulting color after shifting.

    """

    def interpolate(start: float, end: float, factor: float) -> float:
        """Interpolate between two values by a given factor."""
        return start + (end - start) * factor

    # Normalize RGB values
    color_red = int(color.rgb_color[0:2], 16) / 255
    color_green = int(color.rgb_color[2:4], 16) / 255
    color_blue = int(color.rgb_color[4:6], 16) / 255

    target_red = int(target_color.rgb_color[0:2], 16) / 255
    target_green = int(target_color.rgb_color[2:4], 16) / 255
    target_blue = int(target_color.rgb_color[4:6], 16) / 255

    # Interpolate RGB values
    new_red = interpolate(color_red, target_red, factor)
    new_green = interpolate(color_green, target_green, factor)
    new_blue = interpolate(color_blue, target_blue, factor)

    # Convert back to hex
    shifted_color = f"{int(new_red * 255):02x}{int(new_green * 255):02x}{int(new_blue * 255):02x}"
    return Color(shifted_color)
