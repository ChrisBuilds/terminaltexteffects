"""This module provides a collection of functions that generate ANSI escape codes for various terminal formatting effects.
These escape codes can be used to modify the appearance of text in a terminal.
"""

from __future__ import annotations

import re


def parse_ansi_color_sequence(sequence: str) -> int | str:
    """Parses an 8-bit or 24-bit ANSI color sequence and returns the color code as an integer, in the case of 8-bit, or
    a hex string in the case of 24-bit.

    Args:
        sequence (str): ANSI color sequence

    Returns:
        int | str: 8-bit color int or 24-bit color str
    """
    # Remove escape characters
    sequence = re.sub(r"(\033\[|\x1b\[)", "", sequence).strip("m")
    # detect 24-bit colors
    if re.match(r"^(38;2|48;2)", sequence):
        sequence = re.sub(r"^(38;2;|48;2;)", "", sequence)
        colors = []
        for color in sequence.split(";"):
            if color:
                colors.append(int(color))
            else:
                colors.append(0)  # default to 0 if no value in field (e.g. 38;2;;0m)
        return "".join(f"{color:02X}" for color in colors)
    # detect 8-bit colors
    elif re.match(r"^(38;5|48;5)", sequence):
        sequence = re.sub(r"^(38;5;|48;5;)", "", sequence)
        return int(sequence)
    raise ValueError("Invalid ANSI color sequence")


def DEC_SAVE_CURSOR_POSITION() -> str:
    """Saves the cursor position using DEC sequence.

    Returns:
        str: ANSI escape code
    """
    return "\0337"


def DEC_RESTORE_CURSOR_POSITION() -> str:
    """Restores the cursor position using DEC sequence.

    Returns:
        str: ANSI escape code
    """
    return "\0338"


def HIDE_CURSOR() -> str:
    """Hides the cursor.

    Returns:
        str: ANSI escape code
    """
    return "\033[?25l"


def SHOW_CURSOR() -> str:
    """Shows the cursor.

    Returns:
        str: ANSI escape code
    """
    return "\033[?25h"


def MOVE_CURSOR_UP(y: int) -> str:
    """Moves the cursor up y lines.

    Args:
        y (int): number of lines to move up

    Returns:
        str: ANSI escape code
    """
    return f"\033[{y}A"


def MOVE_CURSOR_TO_COLUMN(x: int) -> str:
    """Moves the cursor to the x column.

    Args:
        x (int): column number

    Returns:
        str: ANSI escape code
    """
    return f"\033[{x}G"


def RESET_ALL() -> str:
    """Resets all formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[0m"


def APPLY_BOLD() -> str:
    """Applies bold formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[1m"


def APPLY_DIM() -> str:
    """Applies dim formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[2m"


def APPLY_ITALIC() -> str:
    """Applies italic formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[3m"


def APPLY_UNDERLINE() -> str:
    """Applies underline formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[4m"


def APPLY_BLINK() -> str:
    """Applies blink formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[5m"


def APPLY_REVERSE() -> str:
    """Applies reverse formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[7m"


def APPLY_HIDDEN() -> str:
    """Applies hidden formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[8m"


def APPLY_STRIKETHROUGH() -> str:
    """Applies strikethrough formatting.

    Returns:
        str: ANSI escape code
    """
    return "\033[9m"
