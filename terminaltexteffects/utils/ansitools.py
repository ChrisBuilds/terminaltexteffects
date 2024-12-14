"""Collection of functions that generate ANSI escape codes for various terminal formatting effects.

These escape codes can be used to modify the appearance of text in a terminal.

Functions:
    parse_ansi_color_sequence(sequence: str) -> int | str: Parse an 8-bit or 24-bit ANSI color sequence.
    dec_save_cursor_position() -> str: Save the cursor position using DEC sequence.
    dec_restore_cursor_position() -> str: Restore the cursor position using DEC sequence.
    hide_cursor() -> str: Hide the cursor.
    show_cursor() -> str: Show the cursor.
    move_cursor_up(y: int) -> str: Move the cursor up y lines.
    move_cursor_to_column(x: int) -> str: Move the cursor to the specified column.
    reset_all() -> str: Reset all formatting.
    apply_bold() -> str: Apply bold formatting.
    apply_dim() -> str: Apply dim formatting.
    apply_italic() -> str: Apply italic formatting.
    apply_underline() -> str: Apply underline formatting.
    apply_blink() -> str: Apply blink formatting.
    apply_reverse() -> str: Apply reverse formatting.
    apply_hidden() -> str: Apply hidden formatting.
    apply_strikethrough() -> str: Apply strikethrough formatting.
"""

from __future__ import annotations

import re


def parse_ansi_color_sequence(sequence: str) -> int | str:
    """Parse an 8-bit or 24-bit ANSI color sequence.

    Returns the color code as an integer, in the case of 8-bit, or a hex string in the case of 24-bit.

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
    if re.match(r"^(38;5|48;5)", sequence):
        sequence = re.sub(r"^(38;5;|48;5;)", "", sequence)
        return int(sequence)
    msg = "Invalid ANSI color sequence"
    raise ValueError(msg)


def dec_save_cursor_position() -> str:
    """Save the cursor position using DEC sequence.

    Returns:
        str: ANSI escape code

    """
    return "\0337"


def dec_restore_cursor_position() -> str:
    """Restore the cursor position using DEC sequence.

    Returns:
        str: ANSI escape code

    """
    return "\0338"


def hide_cursor() -> str:
    """Hide the cursor.

    Returns:
        str: ANSI escape code

    """
    return "\033[?25l"


def show_cursor() -> str:
    """Show the cursor.

    Returns:
        str: ANSI escape code

    """
    return "\033[?25h"


def move_cursor_up(y: int) -> str:
    """Move the cursor up y lines.

    Args:
        y (int): number of lines to move up

    Returns:
        str: ANSI escape code

    """
    return f"\033[{y}A"


def move_cursor_to_column(x: int) -> str:
    """Move the cursor to the specified column.

    Args:
        x (int): column number

    Returns:
        str: ANSI escape code

    """
    return f"\033[{x}G"


def reset_all() -> str:
    """Reset all formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[0m"


def apply_bold() -> str:
    """Apply bold formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[1m"


def apply_dim() -> str:
    """Apply dim formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[2m"


def apply_italic() -> str:
    """Apply italic formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[3m"


def apply_underline() -> str:
    """Apply underline formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[4m"


def apply_blink() -> str:
    """Apply blink formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[5m"


def apply_reverse() -> str:
    """Apply reverse formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[7m"


def apply_hidden() -> str:
    """Apply hidden formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[8m"


def apply_strikethrough() -> str:
    """Apply strikethrough formatting.

    Returns:
        str: ANSI escape code

    """
    return "\033[9m"
