import argparse


def color_range(arg: str, min: int = 0, max: int = 255) -> int:
    """Validates that the given argument is a valid xterm color value.

    Args:
        arg (str): argument to validate
        min (int, optional): Minimum color value. Defaults to 0.
        max (int, optional): Maximum color value. Defaults to 255.

    Raises:
        argparse.ArgumentTypeError: Color value is not in range.

    Returns:
        int: Valid xterm color value.
    """
    value = int(arg)
    if min <= value <= max:
        return value
    else:
        raise argparse.ArgumentTypeError(f"Color value has to be between {min} and {max}")
