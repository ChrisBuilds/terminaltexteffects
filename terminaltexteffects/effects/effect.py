import random
from dataclasses import dataclass
import terminaltexteffects.utils.terminaloperations as tops
from terminaltexteffects.utils import utils
from terminaltexteffects.effects.effect_char import EffectCharacter


@dataclass
class OutputArea:
    """A class for storing the output area of an effect.

    Args:
        top (int): top row of the output area
        right (int): right column of the output area
        bottom (int): bottom row of the output area. Defaults to 1.
        left (int): left column of the output area. Defaults to 1.

    """

    top: int
    right: int
    bottom: int = 1
    left: int = 1


class Effect:
    """Generic class for all effects. Derive from this class to create a new effect."""

    def __init__(self, input_data: str, animation_rate: float = 0):
        """Initializes the Effect class.

        Args:
            input_data (str): string from stdin
            animation_rate (float, optional): time to sleep between animation steps. Defaults to 0.
        """
        self.input_data = input_data
        self.characters = utils.decompose_input(input_data)
        self.terminal_width, self.terminal_height = tops.get_terminal_dimensions()
        self.characters = [
            character for character in self.characters if character.input_coord.row < self.terminal_height - 1
        ]
        self.animation_rate = animation_rate
        self.input_height = len(input_data.splitlines())
        self.input_width = max([character.input_coord.column for character in self.characters])
        self.output_area = OutputArea(self.input_height, self.input_width)

        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []
        self.completed_chars: list[EffectCharacter] = []

    def prep_terminal(self) -> None:
        """Prepares the terminal for the effect by adding empty lines above."""
        print("\n" * self.input_height)

    def maintain_completed(self) -> None:
        """Print completed characters in case they've been overwritten."""
        for completed_char in self.completed_chars:
            tops.print_character(completed_char)

    def random_column(self) -> int:
        """Returns a random column position."""
        return random.randint(1, self.input_width)

    def random_row(self) -> int:
        """Returns a random row position."""
        return random.randint(1, self.output_area.top)

    def input_by_row(self) -> dict[int, list[EffectCharacter]]:
        """Returns a dict of rows of EffectCharacters where the key is the row index.
        Returns:
            dict[int,list[EffectCharacter]]: dict of rows of EffectCharacters
        """
        rows: dict[int, list[EffectCharacter]] = dict()
        for row_index in range(self.input_height + 1):
            characters_in_row = [character for character in self.characters if character.input_coord.row == row_index]
            if characters_in_row:
                rows[row_index] = characters_in_row
        return rows

    def input_by_column(self) -> dict[int, list[EffectCharacter]]:
        """Returns a dict columns of EffectCharacters where the key is the column index.

        Returns:
            dict[int,list[EffectCharacter]]: dict of columns of EffectCharacters
        """
        columns: dict[int, list[EffectCharacter]] = dict()
        for column_index in range(self.input_width + 1):
            characters_in_column = [
                character for character in self.characters if character.input_coord.column == column_index
            ]
            if characters_in_column:
                columns[column_index] = characters_in_column
        return columns
