import random, argparse
import terminaltexteffects.utils.terminal as terminal
from terminaltexteffects.base_character import EffectCharacter


class Effect:
    """Generic class for all effects. Derive from this class to create a new effect."""

    def __init__(self, terminal: terminal.Terminal, args: argparse.Namespace):
        """Initializes the Effect class.

        Args:
            terminal (terminal.Terminal): a Terminal object
        """
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []

    def random_column(self) -> int:
        """Returns a random column position."""
        return random.randint(1, self.terminal.output_area.right)

    def random_row(self) -> int:
        """Returns a random row position."""
        return random.randint(1, self.terminal.output_area.top)

    def input_by_row(self) -> dict[int, list[EffectCharacter]]:
        """Returns a dict of rows of EffectCharacters where the key is the row index.
        Returns:
            dict[int,list[EffectCharacter]]: dict of rows of EffectCharacters
        """
        rows: dict[int, list[EffectCharacter]] = dict()
        for row_index in range(self.terminal.output_area.top + 1):
            characters_in_row = [
                character for character in self.terminal.characters if character.input_coord.row == row_index
            ]
            if characters_in_row:
                rows[row_index] = characters_in_row
        return rows

    def input_by_column(self) -> dict[int, list[EffectCharacter]]:
        """Returns a dict columns of EffectCharacters where the key is the column index.

        Returns:
            dict[int,list[EffectCharacter]]: dict of columns of EffectCharacters
        """
        columns: dict[int, list[EffectCharacter]] = dict()
        for column_index in range(self.terminal.output_area.right + 1):
            characters_in_column = [
                character for character in self.terminal.characters if character.input_coord.column == column_index
            ]
            if characters_in_column:
                columns[column_index] = characters_in_column
        return columns
