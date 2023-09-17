"""EffectCharacter class and supporting classes to initialize and manage the state of a single character from the input data."""

import typing
from terminaltexteffects.utils import graphics, motion

if typing.TYPE_CHECKING:
    from terminaltexteffects.utils.terminal import Terminal


class EffectCharacter:
    """A single character from the input data. Contains the state of the character.

    An EffectCharacter object contains the symbol, animation units, graphical modes, waypoints, and coordinates for a single
    character from the input data. The EffectCharacter object is used by the Effect class to animate the character.

    Attributes:
        symbol (str): the current symbol used in place of the character.
        is_active (bool): active characters are printed to the terminal.
        input_symbol (str): the symbol for the character in the input data.
    """

    def __init__(self, symbol: str, input_column: int, input_row: int, terminal: "Terminal"):
        """Initializes the EffectCharacter class.

        Args:
            symbol (str): the character symbol.
            input_column (int): the final column position of the character.
            input_row (int): the final row position of the character.
        """
        self.input_symbol: str = symbol
        "The symbol for the character in the input data."
        self.input_coord: motion.Coord = motion.Coord(input_column, input_row)
        "The coordinate of the character in the input data."
        self.symbol: str = symbol
        "The current symbol for the character, determined by the animation units."
        self.terminal: Terminal = terminal
        self.animator: graphics.Animator = graphics.Animator(self)
        self.motion: motion.Motion = motion.Motion(self)
        self.is_active: bool = True
        "Active characters are printed to the terminal."
