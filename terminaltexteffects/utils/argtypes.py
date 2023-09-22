import argparse
from terminaltexteffects.utils.easing import Ease

EASING_EPILOG = """\
    Easing
    ------
    Note: A prefix must be added to the function name.
    
    All easing functions support the following prefixes:
        IN_  - Ease in
        OUT_ - Ease out
        IN_OUT_ - Ease in and out
        
    Easing Functions
    ----------------
    SINE   - Sine easing
    QUAD   - Quadratic easing
    CUBIC  - Cubic easing
    QUART  - Quartic easing
    QUINT  - Quintic easing
    EXPO   - Exponential easing
    CIRC   - Circular easing
    BACK   - Back easing
    ELASTIC - Elastic easing
    BOUNCE - Bounce easing
    
    Visit: https://easings.net/ for visualizations of the easing functions.
"""


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    """Custom formatter for argparse that combines ArgumentDefaultsHelpFormatter and RawDescriptionHelpFormatter."""

    pass


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


def valid_gap(gap_arg: str) -> int:
    """Validates that the given argument is a valid gap value.

    Args:
        gap_arg (str): argument to validate

    Raises:
        argparse.ArgumentTypeError: Gap value is not in range.

    Returns:
        int: validated gap value
    """
    if int(gap_arg) < 0:
        raise argparse.ArgumentTypeError(f"invalid gap value: {gap_arg} is not a valid gap. Gap must be int >= 0.")
    return int(gap_arg)


def valid_animationrate(animationrate_arg: str) -> float:
    """Validates that the given argument is a valid animationrate value.

    Args:
        animationrate_arg (str): argument to validate

    Raises:
        argparse.ArgumentTypeError: Animationrate value is not in range.

    Returns:
        float: validated animationrate value
    """
    if float(animationrate_arg) < 0:
        raise argparse.ArgumentTypeError(
            f"invalid animationrate value: {animationrate_arg} is not a valid animationrate. Animationrate must be float >= 0."
        )
    return float(animationrate_arg)


def valid_speed(speed_arg: str) -> float:
    """Validates that the given argument is a valid speed value.

    Args:
        speed_arg (str): argument to validate

    Raises:
        argparse.ArgumentTypeError: Speed value is not in range.

    Returns:
        float: validated speed value
    """
    if float(speed_arg) <= 0:
        raise argparse.ArgumentTypeError(
            f"invalid speed value: {speed_arg} is not a valid speed. Speed must be float > 0."
        )
    return float(speed_arg)


def valid_ease(ease_arg: str) -> Ease:
    """Validates that the given argument is a valid easing function.

    Args:
        ease_arg (str): argument to validate

    Raises:
        argparse.ArgumentTypeError: Ease value is not a valid easing function.

    Returns:
        Ease: validated ease value
    """
    try:
        return Ease[ease_arg.upper()]
    except KeyError:
        raise argparse.ArgumentTypeError(f"invalid ease value: {ease_arg} is not a valid ease.")


def positive_int(arg: str) -> int:
    """Validates that the given argument is a positive integer.

    Args:
        arg (str): argument to validate

    Returns:
        int: validated positive integer
    """
    if int(arg) > 0:
        return int(arg)
    else:
        raise argparse.ArgumentTypeError(f"invalid value: {arg} is not > 0.")


def ge_zero(arg: str) -> int:
    """Validates that the given argument is an integer greater than or equal to zero.
    Args:
        arg (str): argument to validate

    Returns:
        int: validated integer
    """
    if int(arg) >= 0:
        return int(arg)
    else:
        raise argparse.ArgumentTypeError(f"invalid value: {arg} is not >= 0.")


def is_ascii_or_utf8(s: str) -> bool:
    """Tests if the given string is either ASCII or UTF-8.

    Args:
        s (str): string to test

    Returns:
        bool: True if the string is either ASCII or UTF-8, False otherwise
    """
    try:
        s.encode("ascii")
    except UnicodeEncodeError:
        try:
            s.encode("utf-8")
        except UnicodeEncodeError:
            return False
        else:
            return True
    else:
        return True


def valid_symbol(arg: str) -> str:
    """Validates that the given argument is a valid symbol.

    Args:
        arg (str): argument to validate

    Returns:
        str: validated symbol
    """
    if len(arg) == 1 and is_ascii_or_utf8(arg):
        return arg
    else:
        raise argparse.ArgumentTypeError(
            f"invalid symbol: {arg} is not a valid symbol. Must be a single ASCII/UTF-8 character."
        )
