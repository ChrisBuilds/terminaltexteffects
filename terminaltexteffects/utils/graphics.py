"""Classes for storing and manipulating character graphics.

Classes:
    Color: A Color object represents a color in the RGB color space. The color can be initialized with an XTerm-256
    color code or an RGB hex color string. Can be printed to display the color code and appearance as a color block.
    Gradient: A Gradient is a list of RGB hex color strings transitioning from one color to another. Can be printed to
    display the gradient color spectrum.
"""

import itertools
import typing
from collections.abc import Iterator
from enum import Enum, auto

from terminaltexteffects.utils import ansitools, colorterm, geometry, hexterm

if typing.TYPE_CHECKING:
    pass


class Color:
    """A Color object represents a color in the RGB color space. The color can be initialized with an XTerm-256 color
    code or an RGB hex color string. Can be printed to display the color code and appearance as a color block.

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
        """Initializes a Color object.

        Args:
            color_value (int | str): The color value as an XTerm-256 color code or an RGB hex color string. Example: 255 or 'ffffff' or '#ffffff'

        Raises:
            ValueError: If the color value is not a valid XTerm-256 color code or an RGB hex color string.
        """
        self.color_arg = color_value
        self.xterm_color: int | None = None
        if hexterm.is_valid_color(color_value):
            if isinstance(color_value, int):
                self.xterm_color = color_value
                self.rgb_color = hexterm.xterm_to_hex(color_value)
            else:
                self.rgb_color = color_value.strip("#")
                self.xterm_color = None
        else:
            raise ValueError(
                "Invalid color value. Color must be an XTerm-256 color code or an RGB hex color string. Example: 255 or 'ffffff' or '#ffffff'"
            )

    @property
    def rgb_ints(self) -> tuple[int, int, int]:
        """Returns the RGB values as a tuple of integers.

        Returns:
            tuple[int, int, int]: The RGB values as a tuple of integers.
        """
        return colorterm._hex_to_int(self.rgb_color)

    def __repr__(self) -> str:
        return f"Color({self.color_arg})"

    def __str__(self) -> str:
        color_block = f"{colorterm.fg(self.rgb_color)}█████{ansitools.RESET_ALL()}"
        return f"Color Code: {self.rgb_color}{f' | XTerm Color: {self.xterm_color}' if self.xterm_color else ''}\nColor Appearance: {color_block}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Color):
            return NotImplemented
        return self.color_arg == other.color_arg

    def __ne__(self, other: object) -> bool:
        if not isinstance(other, Color):
            return NotImplemented
        return self.color_arg != other.color_arg

    def __hash__(self) -> int:
        return hash(self.color_arg)

    def __iter__(self) -> Iterator["Color"]:
        return iter((self,))


class Gradient:
    """A Gradient is a list of RGB hex color strings transitioning from one color to another. The gradient color
    list is calculated using linear interpolation based on the provided start and end colors and the number of steps. Gradients
    can be iterated over to get the next color in the gradient color list. If there is only one color in the stops list,
    the gradient will be a list of the same color.

    If multiple steps are given, the gradient between pairs of colors will be equal to the number of steps for the pair
    based on the order of stops and steps.

    Ex: stops = ("ffffff", "aaaaaa", "000000"), steps = (6, 3)

    "fffffff" -> (6 steps) -> "aaaaaa" -> (3 steps) -> "000000"

    The step count includes the stop for each pair. Total number of colors in the resulting gradient spectrum is the sum of the steps between
    each pair of stops plus 1.

    Attributes:
        spectrum (list[str]): List (length=sum(steps) + 1) of RGB hex color strings

    """

    class Direction(Enum):
        """Enum for specifying the direction of the gradient."""

        VERTICAL = auto()
        HORIZONTAL = auto()
        CENTER = auto()
        DIAGONAL = auto()

    def __init__(self, *stops: Color, steps: int | tuple[int, ...] = 1, loop=False) -> None:
        """
        Initializes a Graphics object.

        Args:
            stops (Color): One ore more variables of type Color representing the color stops.
            steps (int | tuple[int, ...], optional): Number of steps or a tuple of step values for generating the
            spectrum. Defaults to 1.
            loop (bool, optional): Loop the gradient. This causes the final gradient color to transition back to the first gradient color. Defaults to False.

        Raises:
            ValueError: If no color stops are provided.

        Attributes:
            _stops (tuple[Color]): Tuple of Color objects representing the color stops.
            _steps (int | tuple[int, ...]): Number of steps or a tuple of step values for generating the spectrum.
            _loop (bool): Loop the gradient. This causes the final gradient color to transition back to the first gradient color.
            spectrum (list[str]): List of strings representing the generated spectrum.
            _index (int): Current index of the spectrum.

        Returns:
            None
        """
        self._stops = stops
        if len(self._stops) < 1:
            raise ValueError("At least one stop must be provided.")
        self._steps = steps
        self._loop = loop
        self.spectrum: list[Color] = self._generate(self._steps)
        self._index: int = 0

    def get_color_at_fraction(self, fraction: float) -> Color:
        """Returns the color at a fraction of the gradient.

        Args:
            fraction (float): The fraction of the gradient to get the color for.

        Returns:
            Color: The color at the fraction of the gradient.
        """
        if fraction < 0 or fraction > 1:
            raise ValueError("Fraction must be 0 <= fraction <= 1.")
        index = round(fraction * (len(self.spectrum) - 1))
        return self.spectrum[index]

    def _generate(self, steps) -> list[Color]:
        """Calculate a gradient of colors between two colors using linear interpolation. If
        there is only one color in the stops tuple, the gradient will be a list of the same color.

        If multiple steps are given, the gradient between pairs of colors will be equal to the number of steps for the pair
        based on the order of stops and steps.

        Ex: stops = ("ffffff", "aaaaaa", "000000"), steps = (6, 3)
        Distance from "ffffff" to "aaaaaa" = 6 steps (7 colors including start and end)
        Distance from "aaaaaa" to "000000" = 3 steps (4 colors including start and end)
        Total colors in the gradient spectrum = 10 ("aaaaaa" is not repeated when transitioning from "ffffff" to "aaaaaa" and from "aaaaaa" to "000000")


        The step count includes the stop for each pair. Total number of colors in the resulting gradient spectrum:
        sum(steps) + 1

        Returns:
            list[str]: List (length=sum(steps) + 1) of RGB hex color strings. The first and last colors are the start and end stops, respectively.
        """
        if isinstance(steps, int):
            steps = (steps,)
            for step in steps:
                if step < 1:
                    raise ValueError("Steps must be greater than 0.")
        spectrum: list[Color] = []
        if len(self._stops) == 1:
            color = self._stops[0]
            for _ in range(steps[0]):
                spectrum.append(color)
            return spectrum
        if self._loop:
            self._stops = self._stops + (self._stops[0],)
        color_pairs = list(itertools.pairwise(self._stops))
        steps = steps[: len(color_pairs)]
        color_pair: tuple[Color, Color]
        for color_pair, steps in itertools.zip_longest(color_pairs, steps, fillvalue=steps[-1]):
            start, end = color_pair
            start_color_ints = start.rgb_ints
            end_color_ints = end.rgb_ints
            # Initialize an empty list to store the gradient colors
            gradient_colors: list[Color] = []
            # Calculate the color deltas for each RGB value
            red_delta = (end_color_ints[0] - start_color_ints[0]) // steps
            green_delta = (end_color_ints[1] - start_color_ints[1]) // steps
            blue_delta = (end_color_ints[2] - start_color_ints[2]) // steps
            # Calculate the intermediate colors and add them to the gradient colors list
            range_start = int(len(spectrum) > 0)  # if this is the first pair, add the start color to the spectrum
            for i in range(range_start, max(steps, 0)):
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
        self, max_row: int, max_column: int, direction: "Gradient.Direction"
    ) -> dict[geometry.Coord, Color]:
        """Builds a mapping of coordinates to colors based on the gradient and a direction.

        For example, a vertical gradient will have the same color for each column in a row. When applied across all characters in the output area, the gradient will be visible as a vertical gradient.

        Args:
            max_row (int): The maximum row value.
            max_column (int): The maximum column value.
            direction (Gradient.Direction): The direction of the gradient.

        Returns:
            dict[Coord, str]: A mapping of coordinates to colors.
        """
        gradient_mapping: dict[geometry.Coord, Color] = {}
        if direction == Gradient.Direction.VERTICAL:
            for row_value in range(max_row + 1):
                if max_row == 0:
                    fraction = 1.0
                else:
                    fraction = row_value / max_row
                color = self.get_color_at_fraction(fraction)
                for column_value in range(1, max_column + 1):
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color
        elif direction == Gradient.Direction.HORIZONTAL:
            for column_value in range(1, max_column + 1):
                if max_column == 0:
                    fraction = 1.0
                else:
                    fraction = column_value / max_column
                color = self.get_color_at_fraction(fraction)
                for row_value in range(max_row + 1):
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color
        elif direction == Gradient.Direction.CENTER:
            for row_value in range(max_row + 1):
                for column_value in range(1, max_column + 1):
                    distance_from_center = geometry.find_normalized_distance_from_center(
                        max_row, max_column, geometry.Coord(column_value, row_value)
                    )
                    color = self.get_color_at_fraction(distance_from_center)
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color
        elif direction == Gradient.Direction.DIAGONAL:
            for row_value in range(max_row + 1):
                for column_value in range(1, max_column + 1):
                    if max_row == 0 or max_column == 0:
                        fraction = 1.0
                    else:
                        fraction = ((row_value * 2) + column_value) / ((max_row * 2) + max_column)
                    color = self.get_color_at_fraction(fraction)
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color

        return gradient_mapping

    def __iter__(self) -> Iterator[Color]:
        yield from self.spectrum

    def __len__(self) -> int:
        return len(self.spectrum)

    def __str__(self) -> str:
        color_blocks = [f"{colorterm.fg(color.rgb_color)}█{ansitools.RESET_ALL()}" for color in self.spectrum]
        return f"Gradient: Stops({', '.join(c.rgb_color for c in self._stops)}), Steps({self._steps})\n" + "".join(
            color_blocks
        )
