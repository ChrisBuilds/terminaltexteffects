"""Convert xterm color codes and hex colors into ANSI escape sequences.

Functions:
    fg(color_code: str | int) -> str: Set the foreground color of the terminal text.
    bg(color_code: str | int) -> str: Set the background color of the terminal text.
"""

from __future__ import annotations


def _hex_to_int(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string into a list of integers.

    Args:
        hex_color (str): Hex color string in the range 000000 -> FFFFFF. '#' is optional.

    Returns:
        tuple[int, int, int]: A tuple of integers [RED, GREEN, BLUE] representing the color in RGB format.

    """
    hex_color = hex_color.strip("#")
    ints = [int(hex_color[i : i + 2], 16) for i in range(0, 6, 2)]
    return ints[0], ints[1], ints[2]


def _color(color_code: str | int, location: int) -> str:
    """Return an ANSI escape sequence to color the foreground/background of text.

    This is a helper function for fg() and bg().

    Args:
        color_code (str | int): The color code to be converted.
        location (int): The location to apply the color.

    Returns:
        str: The ANSI escape sequence for the color.

    Raises:
        ValueError: If the color code is not in the range 000000 -> FFFFFF or 0 -> 255.

    """
    if isinstance(color_code, str):
        color_ints = _hex_to_int(color_code)
        sequence = f"\x1b[{location};2;{color_ints[0]};{color_ints[1]};{color_ints[2]}m"
    elif isinstance(color_code, int):
        if color_code not in range(256):
            msg = f"Got color code ({color_code}): xterm color codes must be an integer: 0 <= n <= 255"
            raise ValueError(msg)
        sequence = f"\x1b[{location};5;{color_code}m"
    else:
        msg = (
            f"Got color code ({color_code}): Color must be either hex string #000000 -> #FFFFFF or"
            f" int xterm color code 0 <= n <= 255"
        )
        raise TypeError(
            msg,
        )
    return sequence


def fg(color_code: str | int) -> str:
    """Set the foreground color of the terminal text.

    Args:
        color_code (str | int): The value to set the foreground color, as a hex string or X-Term 256 color code.

    Returns:
        str: The ANSI escape sequence to set the foreground color.

    """
    return _color(color_code, 38)


def bg(color_code: str | int) -> str:
    """Set the background color of the terminal text.

    Args:
        color_code (str | int): The value to set the background color, as a hex string or X-Term 256 color code.

    Returns:
        str: The ANSI escape sequence to set the background color.

    """
    return _color(color_code, 48)
