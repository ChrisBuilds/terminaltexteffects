from terminaltexteffects.utils import colorterm

"""This file contains ANSI escape codes for terminal formatting."""


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


def format_symbol(symbol: str, graphical_effect) -> str:
    """Formats the symbol for printing.

    Args:
        character (EffectCharacter): the character to format

    Returns:
        str: the formatted symbol
    """
    formatting_string = ""
    if graphical_effect.bold:
        formatting_string += APPLY_BOLD()
    if graphical_effect.italic:
        formatting_string += APPLY_ITALIC()
    if graphical_effect.underline:
        formatting_string += APPLY_UNDERLINE()
    if graphical_effect.blink:
        formatting_string += APPLY_BLINK()
    if graphical_effect.reverse:
        formatting_string += APPLY_REVERSE()
    if graphical_effect.hidden:
        formatting_string += APPLY_HIDDEN()
    if graphical_effect.strike:
        formatting_string += APPLY_STRIKETHROUGH()
    if graphical_effect.color:
        formatting_string += colorterm.fg(graphical_effect.color)

    formatted_symbol = f"{formatting_string}{symbol}{RESET_ALL() if formatting_string else ''}"
    return formatted_symbol
