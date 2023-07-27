"""This file contains ANSI escape codes for terminal formatting."""


class ANSIcodes:
    """ANSI escape codes for terminal formatting."""

    def DEC_SAVE_CURSOR_POSITION(self) -> str:
        """Saves the cursor position using DEC sequence.

        Returns:
            str: ANSI escape code
        """
        return "\0337"

    def DEC_RESTORE_CURSOR_POSITION(self) -> str:
        """Restores the cursor position using DEC sequence.

        Returns:
            str: ANSI escape code
        """
        return "\0338"

    def MOVE_CURSOR_UP(self, y: int) -> str:
        """Moves the cursor up y lines.

        Args:
            y (int): number of lines to move up

        Returns:
            str: ANSI escape code
        """
        return f"\033[{y}A"

    def MOVE_CURSOR_TO_COLUMN(self, x: int) -> str:
        """Moves the cursor to the x column.

        Args:
            x (int): column number

        Returns:
            str: ANSI escape code
        """
        return f"\033[{x}G"

    def RESET_ALL(self) -> str:
        """Resets all formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[0m"

    def APPLY_BOLD(self) -> str:
        """Applies bold formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[1m"

    def APPLY_DIM(self) -> str:
        """Applies dim formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[2m"

    def APPLY_ITALIC(self) -> str:
        """Applies italic formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[3m"

    def APPLY_UNDERLINE(self) -> str:
        """Applies underline formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[4m"

    def APPLY_BLINK(self) -> str:
        """Applies blink formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[5m"

    def APPLY_REVERSE(self) -> str:
        """Applies reverse formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[7m"

    def APPLY_HIDDEN(self) -> str:
        """Applies hidden formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[8m"

    def APPLY_CROSSED_OUT(self) -> str:
        """Applies crossed out formatting.

        Returns:
            str: ANSI escape code
        """
        return "\033[9m"
