"""A module for managing the terminal state and output."""
import shutil
import sys
import time
import argparse
from dataclasses import dataclass

from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils import ansitools


@dataclass
class OutputArea:
    """A class for storing the output area of an effect.

    Args:
        top (int): top row of the output area
        right (int): right column of the output area
        bottom (int): bottom row of the output area. Defaults to 1.
        left (int): left column of the output area. Defaults to 1.

    """

    top: int
    right: int
    bottom: int = 1
    left: int = 1


class Terminal:
    """A class for managing the terminal state and output."""

    def __init__(self, input_data: str, args: argparse.Namespace):
        self.input_data = input_data
        self.width, self.height = self._get_terminal_dimensions()
        self.characters = self._decompose_input(args.xterm_colors, args.no_color)
        self.input_width = max([character.input_coord.column for character in self.characters])
        self.input_height = max([character.input_coord.row for character in self.characters])
        self.output_area = OutputArea(min(self.height - 1, self.input_height), self.input_width)
        self.characters = [
            character for character in self.characters if character.input_coord.row <= self.output_area.top
        ]
        self.animation_rate = args.animation_rate
        self.last_time_printed = time.time()
        self._update_terminal_state()

        self._prep_outputarea()

    def _get_terminal_dimensions(self) -> tuple[int, int]:
        """Gets the terminal dimensions.

        Returns:
            tuple[int, int]: terminal width and height
        """
        try:
            terminal_width, terminal_height = shutil.get_terminal_size()
        except OSError:
            # If the terminal size cannot be determined, return default values
            return 80, 24
        return terminal_width, terminal_height

    @staticmethod
    def get_piped_input() -> str:
        """Gets the piped input from stdin.

        Returns:
            str: string from stdin
        """
        if not sys.stdin.isatty():
            input_data = sys.stdin.read()
            return input_data
        else:
            return ""

    def _decompose_input(self, use_xterm_colors: bool, no_color: bool) -> list[EffectCharacter]:
        """Decomposes the output into a list of Character objects containing the symbol and its row/column coordinates
        relative to the input display location.

        Coordinates are relative to the cursor row position at the time of execution. 1,1 is the bottom left corner of the row
        above the cursor.

        Args:
            use_xterm_colors (bool): whether to convert colors to the closest XTerm-256 color

        Returns:
            list[Character]: list of EffectCharacter objects
        """
        wrapped_lines = []
        if not self.input_data.strip():
            self.input_data = "No Input."
        input_lines = self.input_data.splitlines()
        for line in input_lines:
            while len(line) > self.width:
                wrapped_lines.append(line[: self.width])
                line = line[self.width :]
            wrapped_lines.append(line)
        input_height = len(wrapped_lines)
        input_characters = []
        for row, line in enumerate(wrapped_lines):
            for column, symbol in enumerate(line):
                if symbol != " ":
                    character = EffectCharacter(symbol, column + 1, input_height - row, self)
                    character.animator.use_xterm_colors = use_xterm_colors
                    character.animator.no_color = no_color
                    input_characters.append(character)
        return input_characters

    def _update_terminal_state(self):
        """Update the internal representation of the terminal state with the current position
        of all active characters.
        """
        rows = [[" " for _ in range(self.output_area.right)] for _ in range(self.output_area.top)]
        for character in self.characters:
            if character.is_active:
                try:
                    # do not allow characters to wrap around the terminal via negative coordinates
                    if character.motion.current_coord.row <= 0 or character.motion.current_coord.column <= 0:
                        continue
                    rows[character.motion.current_coord.row - 1][
                        character.motion.current_coord.column - 1
                    ] = character.symbol
                except IndexError:
                    # ignore characters that are outside the output area
                    pass
        terminal_state = ["".join(row) for row in rows]
        self.terminal_state = terminal_state

    def _prep_outputarea(self) -> None:
        """Prepares the terminal for the effect by adding empty lines above."""
        print("\n" * self.output_area.top)

    def print(self):
        """Prints the current terminal state to stdout while preserving the cursor position."""
        self._update_terminal_state()
        time_since_last_print = time.time() - self.last_time_printed
        if time_since_last_print < self.animation_rate:
            time.sleep(self.animation_rate - time_since_last_print)
        output = "\n".join(self.terminal_state[::-1])
        sys.stdout.write(ansitools.DEC_SAVE_CURSOR_POSITION())
        sys.stdout.write(ansitools.MOVE_CURSOR_UP(self.output_area.top))
        sys.stdout.write(ansitools.MOVE_CURSOR_TO_COLUMN(1))
        sys.stdout.write(output)
        sys.stdout.write(ansitools.DEC_RESTORE_CURSOR_POSITION())
        sys.stdout.flush()
        self.last_time_printed = time.time()
