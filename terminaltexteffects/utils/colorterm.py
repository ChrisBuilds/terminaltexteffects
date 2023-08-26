"""Converts xterm color codes and hex colors into ANSI escape sequences."""


RESET = "\x1b[0m"


def _hex_to_int(hex_color: str) -> list[int]:
    """
    Convert a hex color string into a list of ints.

    Parameters
    ----------
    hex_color : str : Hex color string. '#' is optional.

    Returns
    -------
    List[int] : [RED, GREEN, BLUE] list of color integers
    """
    hex_color = hex_color.strip("#")
    ints = [int(hex_color[i : i + 2], 16) for i in range(0, 6, 2)]
    return ints


def _color(color_code: str | int, location: int) -> str:
    """
    Returns an ANSI escape sequence to color the foreground/background of text following the returned sequence.
    Parameters
    ----------
    color_code : Union[str, int]
    location : int

    Returns
    -------
    str
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
    """Returns an ANSI escape sequence to color the foreground of text following the returned sequence.

    Parameters
    ----------
    color_code : Union[str, int] : Hex color string or xterm color int 0 <= n <= 255

    Returns
    -------
    str : ANSI escape sequence
    """
    sequence = _color(color_code, 38)
    return sequence


def bg(color_code: str | int) -> str:
    """Returns an ANSI escape sequence to color the background of text following the returned sequence.

    Parameters
    ----------
    color_code : Union[str, int] : Hex color string or xterm color int 0 <= n <= 255

    Returns
    -------
    str : ANSI escape sequence
    """
    sequence = _color(color_code, 48)
    return sequence
