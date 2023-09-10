"""EffectCharacter class and supporting classes to initialize and manage the state of a single character from the input data."""

from dataclasses import dataclass

from terminaltexteffects.utils import graphics, motion


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
        self.motion: motion.Motion = motion.Motion(self)
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
        self.motion.move()

    def is_movement_complete(self) -> bool:
        """Returns whether the character has reached the final coordinate.

        Returns:
            bool: True if the character has reached the final coordinate, False otherwise.
        """
        if self.current_coord == self.input_coord:
            return True
        return False
