"""Classes for storing and manipulating character graphics."""

import itertools
import typing
from enum import Enum, auto

from terminaltexteffects.utils import colorterm, geometry, hexterm

if typing.TYPE_CHECKING:
    pass

Color: typing.TypeAlias = int | str


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

    Args:
        *stops (Color): RGB hex color strings or XTerm-256 color codes. Each stop will have steps number of frames between it and the next stop.
        steps tuple[int, ...] | int: Number of steps from the start to the end stop. If multiple steps are given, steps and stops will be paired.

    Attributes:
        spectrum (list[str]): List (length=sum(steps) + 1) of RGB hex color strings

    """

    class Direction(Enum):
        """Enum for specifying the direction of the gradient."""

        VERTICAL = auto()
        HORIZONTAL = auto()
        CENTER = auto()
        DIAGONAL = auto()

    def __init__(self, *stops: Color, steps: int | tuple[int, ...] = 1) -> None:
        self.stops = stops
        if len(self.stops) < 1:
            raise ValueError("At least one stop must be provided.")
        self.steps = steps
        self.spectrum: list[str] = self._generate(self.steps)
        self.index: int = 0

    def get_color_at_fraction(self, fraction: float) -> Color:
        """Returns the color at a fraction of the gradient.

        Args:
            fraction (float): The fraction of the gradient to get the color for.

        Returns:
            str: The color at the fraction of the gradient.
        """
        if fraction < 0 or fraction > 1:
            raise ValueError("Fraction must be 0 <= fraction <= 1.")
        index = round(fraction * (len(self.spectrum) - 1))
        return self.spectrum[index]

    def _generate(self, steps) -> list[str]:
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
        spectrum: list[str] = []
        if len(self.stops) == 1:
            color = self.stops[0]
            if isinstance(color, int):
                color = hexterm.xterm_to_hex(color)
            for _ in range(steps[0]):
                spectrum.append(color)
            return spectrum
        color_pairs = list(itertools.pairwise(self.stops))
        steps = steps[: len(color_pairs)]
        for color_pair, steps in itertools.zip_longest(color_pairs, steps, fillvalue=steps[-1]):
            start, end = color_pair
            # Convert start_color to hex if it's an XTerm-256 color code
            if isinstance(start, int):
                start = hexterm.xterm_to_hex(start)
            # Convert end_color to hex if it's an XTerm-256 color code
            if isinstance(end, int):
                end = hexterm.xterm_to_hex(end)
            # Convert start_color to a list of RGB values
            start_color_ints = colorterm._hex_to_int(start)
            # Convert end_color to a list of RGB values
            end_color_ints = colorterm._hex_to_int(end)
            # Initialize an empty list to store the gradient colors
            gradient_colors: list[str] = []
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
                gradient_colors.append(f"{red:02x}{green:02x}{blue:02x}")
            # Add the end color to the gradient colors list
            gradient_colors.append(end)
            spectrum.extend(gradient_colors)
        return spectrum

    def build_coordinate_color_mapping(
        self, max_row: int, max_column: int, direction: "Gradient.Direction"
    ) -> dict[geometry.Coord, Color]:
        """Builds a mapping of coordinates to colors based on the gradient and a direction.

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
                fraction = row_value / max_row
                color = self.get_color_at_fraction(fraction)
                for column_value in range(1, max_column + 1):
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color
        elif direction == Gradient.Direction.HORIZONTAL:
            for column_value in range(1, max_column + 1):
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
                    fraction = ((row_value * 2) + column_value) / ((max_row * 2) + max_column)
                    color = self.get_color_at_fraction(fraction)
                    gradient_mapping[geometry.Coord(column_value, row_value)] = color

        return gradient_mapping

    def __iter__(self) -> "Gradient":
        self.index = 0
        return self

    def __next__(self) -> str:
        if self.index < len(self.spectrum):
            color = self.spectrum[self.index]
            self.index += 1
            return color
        else:
            raise StopIteration

    def __len__(self) -> int:
        return len(self.spectrum)

    def __str__(self) -> str:
        color_blocks = [f"{colorterm.fg(color)}█{colorterm.RESET}" for color in self.spectrum]
        return f"Gradient: Stops({self.stops}), Steps({self.steps})\n" + "".join(color_blocks)
