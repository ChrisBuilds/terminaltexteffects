import argparse


def valid_color(color_string) -> int | str:
    """Validates that the given argument is a valid color value.

    Args:
        color_string (str): argument to validate

    Raises:
        argparse.ArgumentTypeError: Color value is not in range.

    Returns:
        int | str : validated color value
    """
    xterm_min = 0
    xterm_max = 255
    if len(color_string) == 6:
        # Check if the hex value is a valid color
        if not 0 <= int(color_string, 16) <= 16777215:
            raise argparse.ArgumentTypeError(f"invalid color value: {color_string} is not a valid hex color.")
        return color_string
    else:
        # Check if the color is a valid xterm color
        if not xterm_min <= int(color_string) <= xterm_max:
            raise argparse.ArgumentTypeError(f"invalid color value: {color_string} is not a valid xterm color (0-255).")
        return int(color_string)


def valid_duration(duration_arg: str) -> int:
    """Validates that the given argument is a valid duration value.

    Args:
        duration_arg (str): argument to validate

    Raises:
        argparse.ArgumentTypeError: Duration value is not in range.

    Returns:
        int: validated duration value
    """
    if int(duration_arg) < 1:
        raise argparse.ArgumentTypeError(
            f"invalid duration value: {duration_arg} is not a valid duration. Duration must be int >= 1."
        )
    return int(duration_arg)
