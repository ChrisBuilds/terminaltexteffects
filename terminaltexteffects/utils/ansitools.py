"""Collection of functions that generate ANSI escape codes for various terminal formatting effects.

These escape codes can be used to modify the appearance of text in a terminal.

Functions:
    dec_save_cursor_position() -> str: Save the cursor position using DEC sequence.
    dec_restore_cursor_position() -> str: Restore the cursor position using DEC sequence.
    hide_cursor() -> str: Hide the cursor.
    show_cursor() -> str: Show the cursor.
    move_cursor_up(y: int) -> str: Move the cursor up y lines.
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
    """Move the cursor up by a relative number of rows.

    A distance of `0` is a no-op and returns an empty string.

    Args:
        y (int): Number of rows to move upward from the current cursor position.

    Returns:
        str: ANSI escape code

    Raises:
        TypeError: If `y` is not a non-boolean integer.
        ValueError: If `y` is negative.

    """
    if isinstance(y, bool) or not isinstance(y, int):
        msg = "y must be a non-boolean integer"
        raise TypeError(msg)
    if y < 0:
        msg = "y must be non-negative"
        raise ValueError(msg)
    if y == 0:
        return ""
    return f"\033[{y}A"


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
