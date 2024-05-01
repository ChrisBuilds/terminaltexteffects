"""This module converts xterm color codes and hex colors into ANSI escape sequences."""


def _hex_to_int(hex_color: str) -> list[int]:
    """Converts a hex color string into a list of integers.

    Args:
        hex_color (str): Hex color string. '#' is optional.

    Returns:
        list[int]: A list of integers [RED, GREEN, BLUE] representing the color in RGB format.
    """
    hex_color = hex_color.strip("#")
    ints = [int(hex_color[i : i + 2], 16) for i in range(0, 6, 2)]
    return ints


def _color(color_code: str | int, location: int) -> str:
    """Returns an ANSI escape sequence to color the foreground/background of text. This is a helper function for fg() and bg().

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
        if color_code not in range(0, 256):
            raise ValueError("Got color code ({color_code}): xterm color codes must be an integer: 0 <= n <= 255")
        else:
            sequence = f"\x1b[{location};5;{color_code}m"
    else:
        raise ValueError(
            f"Got color code ({color_code}): Color must be either hex string #000000 -> #FFFFFF or"
            f" int xterm color code 0 <= n <= 255"
        )
    return sequence


def fg(color_code: str | int) -> str:
    """
    Sets the foreground color of the terminal text.

    Args:
        color_code (str | int): The value to set the foreground color, as a hex string or X-Term 256 color code.

    Returns:
        str: The ANSI escape sequence to set the foreground color.

    """
    sequence = _color(color_code, 38)
    return sequence


def bg(color_code: str | int) -> str:
    """
    Sets the background color of the terminal text.

    Args:
        color_code (str | int): The value to set the background color, as a hex string or X-Term 256 color code.

    Returns:
        str: The ANSI escape sequence to set the background color.

    """
    sequence = _color(color_code, 48)
    return sequence
