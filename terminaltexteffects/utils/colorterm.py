"""Convert XTerm 256 color codes and RGB hex colors into ANSI escape sequences.

Functions:
    `fg`: Set the foreground color using an XTerm code or RGB hex string.
    `bg`: Set the background color using an XTerm code or RGB hex string.
"""

from __future__ import annotations

from functools import lru_cache

from terminaltexteffects.utils import hexterm

_XTERM_COLOR_SEQUENCES = {
    location: tuple(f"\x1b[{location};5;{color_code}m" for color_code in range(256)) for location in (38, 48)
}


@lru_cache(maxsize=1024)
def _hex_to_int(hex_color: str) -> tuple[int, int, int]:
    """Convert a hex color string into an RGB integer tuple.

    Args:
        hex_color (str): Exactly six hexadecimal digits with an optional single leading `#`.

    Returns:
        tuple[int, int, int]: A tuple of integers (red, green, blue) representing the color.

    Raises:
        ValueError: If `hex_color` is not exactly six hexadecimal digits with at most one leading `#`.

    """
    color_string = hex_color[1:] if hex_color.startswith("#") else hex_color
    if not hexterm.is_valid_color(hex_color):
        msg = f"Invalid RGB hex color code: {hex_color}"
        raise ValueError(msg)
    return (
        int(color_string[0:2], 16),
        int(color_string[2:4], 16),
        int(color_string[4:6], 16),
    )


@lru_cache(maxsize=1024)
def _truecolor_sequence(hex_color: str, location: int) -> str:
    """Return a cached ANSI RGB sequence for one color and SGR location."""
    red, green, blue = _hex_to_int(hex_color)
    return f"\x1b[{location};2;{red};{green};{blue}m"


def _color(color_code: str | int, location: int) -> str:
    """Return an ANSI escape sequence to color the foreground/background of text.

    This is a helper function for `fg` and `bg`.

    Args:
        color_code (str | int): The color code to be converted.
        location (int): ANSI SGR color selector, where `38` applies foreground color
            and `48` applies background color.

    Returns:
        str: The ANSI escape sequence for the color.

    Raises:
        TypeError: If `color_code` is not a string or non-boolean integer.
        ValueError: If `color_code` is not exactly six hexadecimal digits with at most one leading `#`, or an integer
            from 0 through 255.

    """
    if isinstance(color_code, str):
        sequence = _truecolor_sequence(color_code, location)
    elif isinstance(color_code, int) and not isinstance(color_code, bool):
        if color_code not in range(256):
            msg = f"Got color code ({color_code}): xterm color codes must be an integer: 0 <= n <= 255"
            raise ValueError(msg)
        try:
            sequence = _XTERM_COLOR_SEQUENCES[location][color_code]
        except KeyError:
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
        color_code (str | int): The foreground color as an XTerm 256 color code
            or an RGB hex string, with or without a leading `#`.

    Returns:
        str: The ANSI escape sequence to set the foreground color.

    Raises:
        TypeError: If `color_code` is not a string or non-boolean integer.
        ValueError: If `color_code` is not exactly six hexadecimal digits with at most one leading `#`, or an integer
            from 0 through 255.

    """
    return _color(color_code, 38)


def bg(color_code: str | int) -> str:
    """Set the background color of the terminal text.

    Args:
        color_code (str | int): The background color as an XTerm 256 color code
            or an RGB hex string, with or without a leading `#`.

    Returns:
        str: The ANSI escape sequence to set the background color.

    Raises:
        TypeError: If `color_code` is not a string or non-boolean integer.
        ValueError: If `color_code` is not exactly six hexadecimal digits with at most one leading `#`, or an integer
            from 0 through 255.

    """
    return _color(color_code, 48)
