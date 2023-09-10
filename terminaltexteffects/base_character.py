"""EffectCharacter class and supporting classes to initialize and manage the state of a single character from the input data."""

from dataclasses import dataclass

from terminaltexteffects.utils import graphics


@dataclass
class Coord:
    """A coordinate with row and column values.

    Args:
        column (int): column value
        row (int): row value"""

    column: int
    row: int


@dataclass
class Speed:
    """A class to manage the speed of a character.

    Args:
        minimum (float): minimum speed. Defaults to 0.001.
        maximum (float): maximum speed. Defaults to 5.
        current (float): current speed. Defaults to 1.
        acceleration (float): acceleration. Defaults to 0.
    """

    minimum: float = 0.001
    maximum: float = 5
    current: float = 1
    acceleration: float = 0
    origin_coord: Coord | None = None
    target_coord: Coord | None = None

    def accelerate(self) -> float:
        """Calculates the next speed based on the current speed and acceleration.

        Returns:
            float: speed
        """
        self.current = max(self.minimum, min(self.current + self.acceleration, self.maximum))

    def slow_on_approach(self) -> float:
        """Calculates the acceleration as a function of distance remaining to the target."""


class EffectCharacter:
    """A single character from the input data. Contains the state of the character.

    An EffectCharacter object contains the symbol, animation units, graphical modes, waypoints, and coordinates for a single
    character from the input data. The EffectCharacter object is used by the Effect class to animate the character.

    Attributes:
        symbol (str): the current symbol used in place of the character.
        is_active (bool): active characters are printed to the terminal.
        input_symbol (str): the symbol for the character in the input data.
        animation_units (list[AnimationUnit]): a list of AnimationUnit objects containing the animation units for the character.
        final_coord (Coord): the final coordinate of the character.
        current_coord (Coord): the current coordinate of the character. If different from the final coordinate, the character is moving.
        last_coord (Coord): the last coordinate of the character. Used to clear the last position of the character.
        target_coord (Coord): the target coordinate of the character. Used to determine the next coordinate to move to.
        waypoints (list[Coord]): a list of coordinates to move to. Used to determine the next target coordinate to move to.
        graphical_effect (GraphicalEffect): the current graphical effect for the character.
    """

    def __init__(self, symbol: str, input_column: int, input_row: int):
        """Initializes the EffectCharacter class.

        Args:
            symbol (str): the character symbol.
            input_column (int): the final column position of the character.
            input_row (int): the final row position of the character.
        """
        self.is_active: bool = True
        "Active characters are printed to the terminal."
        self.symbol: str = symbol
        "The current symbol for the character, determined by the animation units."
        self.input_symbol: str = symbol
        "The symbol for the character in the input data."
        self.animator: graphics.Animator = graphics.Animator(self)
        self.input_coord: Coord = Coord(input_column, input_row)
        "The coordinate of the character in the input data."
        self.current_coord: Coord = Coord(input_column, input_row)
        "The current coordinate of the character. If different from the final coordinate, the character is moving."
        self.origin: Coord = Coord(input_column, input_row)
        "The origin coordinate is the explicitly set coordinate, or waypoint, of the character. Used for relative speed calculations."
        self.previous_coord: Coord = Coord(-1, -1)
        "The last coordinate of the character. Used to clear the last position of the character."
        self.target_coord: Coord = Coord(input_column, input_row)
        "The target coordinate of the character. Used to determine the next coordinate to move to."
        self.waypoints: list[Coord] = []
        "A list of coordinates to move to. Used to determine the next target coordinate to move to."
        self.speed = Speed()
        # move_delta is the floating point distance to move each step
        self.move_delta: float = 0
        self.row_delta: float = 0
        self.column_delta: float = 0
        # tweened_column and tweened_row are the floating point values for the current column and row positions
        self.tweened_column: float = 0
        self.tweened_row: float = 0

    def move(self) -> None:
        """Moves the character one step closer to the target position based on speed and acceleration."""
        self.previous_coord.column, self.previous_coord.row = self.current_coord.column, self.current_coord.row
        # set the origin coordinate to the current coordinate if the origin has not been otherwise set
        if self.origin.column == self.input_coord.column and self.origin.row == self.input_coord.row:
            self.origin.column, self.origin.row = self.current_coord.column, self.current_coord.row
        self.speed.accelerate()

        # if the character has reached the target coordinate, pop the next coordinate from the waypoints list
        # and reset the move_delta for recalculation
        if self.current_coord == self.target_coord and self.waypoints:
            self.target_coord = self.waypoints.pop(0)
            self.origin.column, self.origin.row = self.current_coord.column, self.current_coord.row
            self.move_delta = 0

        column_distance = abs(self.current_coord.column - self.target_coord.column)
        row_distance = abs(self.current_coord.row - self.target_coord.row)
        # on first call, calculate the column and row movement distance to approximate an angled line
        if not self.move_delta:
            self.tweened_column = self.current_coord.column
            self.tweened_row = self.current_coord.row
            self.move_delta = min(column_distance, row_distance) / max(column_distance, row_distance, 1)
            if self.move_delta == 0:
                self.move_delta = 1

            if column_distance < row_distance:
                self.column_delta = self.move_delta
                self.row_delta = 1
            elif row_distance < column_distance:
                self.row_delta = self.move_delta
                self.column_delta = 1
            else:
                self.column_delta = self.row_delta = 1
        # if the speed is high enough to jump over the target coordinate, set the current coordinate to the target coordinate
        if abs(self.current_coord.column - self.target_coord.column) < self.column_delta * self.speed.current:
            self.current_coord.column = self.target_coord.column
        if abs(self.current_coord.row - self.target_coord.row) < self.row_delta * self.speed.current:
            self.current_coord.row = self.target_coord.row
        # adjust the column and row positions by the calculated delta, round down to int
        if self.current_coord.column < self.target_coord.column:
            self.tweened_column += self.column_delta * self.speed.current
            self.current_coord.column = int(self.tweened_column)
        elif self.current_coord.column > self.target_coord.column:
            self.tweened_column -= self.column_delta * self.speed.current
            self.current_coord.column = int(self.tweened_column)
        if self.current_coord.row < self.target_coord.row:
            self.tweened_row += self.row_delta * self.speed.current
            self.current_coord.row = int(self.tweened_row)
        elif self.current_coord.row > self.target_coord.row:
            self.tweened_row -= self.row_delta * self.speed.current
            self.current_coord.row = int(self.tweened_row)

    def is_movement_complete(self) -> bool:
        """Returns whether the character has reached the final coordinate.

        Returns:
            bool: True if the character has reached the final coordinate, False otherwise.
        """
        if self.current_coord == self.input_coord:
            return True
        return False
