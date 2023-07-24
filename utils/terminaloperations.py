"""This module contains functions for terminal operations."""

import shutil
import sys


def get_terminal_dimensions() -> tuple[int, int]:
    """Returns the terminal dimensions.

    Returns:
        tuple[int, int]: width, height
    """
    terminal_width, terminal_height = shutil.get_terminal_size()
    return terminal_width, terminal_height


def print_character_at_relative_position(character: str, x: int, y: int) -> None:
    """Moves the cursor to a relative position on the terminal window.

    Args:
        character (str): character to print
        x (int): x position
        y (int): y as number of rows above the current cursor position
    """

    # save cursor position using DEC sequence
    sys.stdout.write("\0337")
    # move cursor y lines up
    sys.stdout.write(f"\033[{y}A")
    # move cursor to x column
    sys.stdout.write(f"\033[{x}G")
    # print character
    sys.stdout.write(character)
    # restore cursor position using DEC sequence
    sys.stdout.write("\0338")
    sys.stdout.flush()


def get_piped_input() -> str:
    """Returns the piped input.

    Returns:
        str: piped input
    """
    if not sys.stdin.isatty():
        with sys.stdin as stdin:
            input_data = sys.stdin.read()
            return input_data
    else:
        return ""
