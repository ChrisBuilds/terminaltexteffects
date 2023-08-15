"""This module contains functions for terminal operations."""
from terminaltexteffects.utils import ansicodes, colorterm
from terminaltexteffects.base_character import EffectCharacter
import shutil
import sys


def get_terminal_dimensions() -> tuple[int, int]:
    """Returns the terminal dimensions.

    Returns:
        tuple[int, int]: width, height
    """
    terminal_width, terminal_height = shutil.get_terminal_size()
    return terminal_width, terminal_height


def print_character(character: EffectCharacter, clear_last: bool = False) -> None:
    """Moves the cursor on the terminal window and prints the character. Will optionally clear the last
    location of the character.

    Args:
        character (EffectCharacter): EffectCharacter object
        clear_last (bool, optional): Whether to clear the last character. Defaults to False.
    """

    def move_and_print(symbol, row, column) -> None:
        """Handle managing the cursor and printing the character.

        Attributes:
            symbol (str): the character symbol.
            row (int): the row position of the character.
            column (int): the column position of the character."""
        sys.stdout.write(ansicodes.DEC_SAVE_CURSOR_POSITION())
        sys.stdout.write(ansicodes.MOVE_CURSOR_UP(row))
        sys.stdout.write(ansicodes.MOVE_CURSOR_TO_COLUMN(column))
        sys.stdout.write(symbol)
        sys.stdout.write(ansicodes.DEC_RESTORE_CURSOR_POSITION())
        sys.stdout.flush()

    formatted_symbol = ""
    if character.graphical_effect.bold:
        formatted_symbol += ansicodes.APPLY_BOLD()
    if character.graphical_effect.dim:
        formatted_symbol += ansicodes.APPLY_DIM()
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
    move_and_print(formatted_symbol, character.current_coord.row, character.current_coord.column)
    if clear_last and character.previous_coord != character.current_coord:
        move_and_print(" ", character.previous_coord.row, character.previous_coord.column)


def get_piped_input() -> str:
    """Returns the piped input.

    Returns:
        str: piped input
    """
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
        return input_data
    else:
        return ""


def decompose_input(input_data: str) -> list[EffectCharacter]:
    """Decomposes the output into a list of Character objects containing the symbol and its row/column coordinates
    relative to the input display location.

    Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left corner of the row
    above the cursor.

    Args:
        input_data (str): string from stdin

    Returns:
        list[Character]: list of EffectCharacter objects
    """
    output_lines = input_data.splitlines()
    input_height = len(output_lines)
    output_characters = []
    for row, line in enumerate(output_lines):
        for column, symbol in enumerate(line):
            if symbol != " ":
                output_characters.append(EffectCharacter(symbol, column + 1, input_height - row))
    return output_characters
