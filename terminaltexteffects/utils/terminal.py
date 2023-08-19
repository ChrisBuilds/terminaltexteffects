from terminaltexteffects.utils import ansicodes, colorterm
from terminaltexteffects.base_character import EffectCharacter
import shutil
import sys
from dataclasses import dataclass


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


class Terminal:
    def __init__(self):
        self.width, self.height = self.get_terminal_dimensions()
        self.input_data = self.get_piped_input()
        self.characters = self.decompose_input()
        self.input_width = max([character.input_coord.column for character in self.characters])
        self.input_height = max([character.input_coord.row for character in self.characters])
        self.terminal_state = self.update_terminal_state()
        self.output_area = OutputArea(min(self.height, self.input_height), self.input_width)

    def get_terminal_dimensions(self) -> tuple[int, int]:
        """Returns the terminal dimensions.

        Returns:
            tuple[int, int]: width, height
        """
        terminal_width, terminal_height = shutil.get_terminal_size()
        return terminal_width, terminal_height

    def get_piped_input(self) -> str:
        """Gets the piped input from stdin.

        Returns:
            str: string from stdin
        """
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            return input_data
        else:
            return ""

    def decompose_input(self) -> list[EffectCharacter]:
        """Decomposes the output into a list of Character objects containing the symbol and its row/column coordinates
        relative to the input display location.

        Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left corner of the row
        above the cursor.

        Returns:
            list[Character]: list of EffectCharacter objects
        """
        wrapped_lines = []
        input_lines = self.input_data.splitlines()
        for line in input_lines:
            while len(line) > self.width:
                wrapped_lines.append(line[: self.width])
                line = line[self.width :]
            if line:
                wrapped_lines.append(line)
        input_height = len(wrapped_lines)
        input_characters = []
        for row, line in enumerate(wrapped_lines):
            for column, symbol in enumerate(line):
                if symbol != " ":
                    input_characters.append(EffectCharacter(symbol, column + 1, input_height - row))
        return input_characters

    def format_symbol(self, character: EffectCharacter) -> str:
        """Formats the symbol for printing.

        Args:
            character (EffectCharacter): the character to format

        Returns:
            str: the formatted symbol
        """
        formatted_symbol = ""
        if character.graphical_effect.bold:
            formatted_symbol += ansicodes.APPLY_BOLD()
        if character.graphical_effect.italic:
            formatted_symbol += ansicodes.APPLY_ITALIC()
        if character.graphical_effect.underline:
            formatted_symbol += ansicodes.APPLY_UNDERLINE()
        if character.graphical_effect.blink:
            formatted_symbol += ansicodes.APPLY_BLINK()
        if character.graphical_effect.reverse:
            formatted_symbol += ansicodes.APPLY_REVERSE()
        if character.graphical_effect.hidden:
            formatted_symbol += ansicodes.APPLY_HIDDEN()
        if character.graphical_effect.strike:
            formatted_symbol += ansicodes.APPLY_STRIKETHROUGH()
        if character.graphical_effect.color:
            formatted_symbol += colorterm.fg(character.graphical_effect.color)

        formatted_symbol = f"{formatted_symbol}{character.symbol}{ansicodes.RESET_ALL() if formatted_symbol else ''}"
        return formatted_symbol

    def update_terminal_state(self) -> list[str]:
        """Update the internal representation of the terminal state with the current position
        of all active characters.

        Returns:
            list[str]: the terminal state, as a list of rows
        """
        characters_strings = [[" " for _ in range(self.width)] for _ in range(self.height)]
        for character in self.characters:
            if character.is_active:
                relative_row = (self.output_area.top - 1) - character.current_coord.row
                characters_strings[relative_row][character.current_coord.column] = self.format_symbol(character)
        terminal_state = ["".join(row) for row in characters_strings]
        return terminal_state

    def print(self):
        self.update_terminal_state()
        for row_index, row in enumerate(self.terminal_state):
            sys.stdout.write(ansicodes.DEC_SAVE_CURSOR_POSITION())
            sys.stdout.write(ansicodes.MOVE_CURSOR_UP(row_index))
            sys.stdout.write(ansicodes.MOVE_CURSOR_TO_COLUMN(1))
            sys.stdout.write(row)
            sys.stdout.write(ansicodes.DEC_RESTORE_CURSOR_POSITION())
            sys.stdout.flush()
