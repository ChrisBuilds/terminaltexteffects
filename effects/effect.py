import random
import utils.terminaloperations as tops
from utils import utils
from effects.effect_char import EffectCharacter


class Effect:
    """Generic class for all effects. Derive from this class to create a new effect."""

    def __init__(self, input_data: str, animation_rate: float = 0):
        """Initializes the Effect class.

        Args:
            input_data (str): string from stdin
        """
        self.input_data = input_data
        self.animation_rate = animation_rate
        self.terminal_width, self.terminal_height = tops.get_terminal_dimensions()
        self.characters = utils.decompose_input(input_data)
        self.characters = [
            character for character in self.characters if character.final_coord.row < self.terminal_height - 1
        ]
        self.input_height = len(input_data.splitlines())
        self.input_width = max([character.final_coord.column for character in self.characters])
        self.output_area_top = min(self.terminal_height - 1, self.input_height)
        "Distance to the top row of the adjusted output area. Top of the terminal if input is too long."
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
        return random.randint(0, self.input_width - 1)

    def random_row(self) -> int:
        """Returns a random row position."""
        return random.randint(0, self.output_area_top)

    def input_by_row(self) -> list[list[EffectCharacter]]:
        """Returns a list of lists of EffectCharacters, grouped by row."""
        input_by_row: list[list[EffectCharacter]] = []
        for row in range(self.input_height):
            characters_in_row = [character for character in self.characters if character.final_coord.row == row]
            if characters_in_row:
                input_by_row.append(characters_in_row)
        return input_by_row

    def input_by_column(self) -> list[list[EffectCharacter]]:
        """Returns a list of lists of EffectCharacters, grouped by column. Columns are orders left to right, top to bottom."""
        input_by_column: list[list[EffectCharacter]] = []
        for column in range(self.input_width + 1):
            characters_in_column = [
                character for character in self.characters if character.final_coord.column == column
            ]
            if characters_in_column:
                input_by_column.append(characters_in_column)
        return input_by_column
