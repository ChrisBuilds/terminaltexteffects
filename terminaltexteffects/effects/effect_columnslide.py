import time
import argparse
import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects import base_effect, base_character
from enum import Enum, auto


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "columnslide",
        help="Slides each column into place.",
        description="columnslide | Slides each column into place.",
        epilog="Example: terminaltexteffects columnslide -a 0.003 --slide-direction up",
    )
    effect_parser.set_defaults(effect_class=ColumnSlide)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.003,
        help="Time to sleep between animation steps. Defaults to 0.003 seconds.",
    )
    effect_parser.add_argument(
        "--slide-direction",
        default="down",
        choices=["up", "down"],
        help="Direction the text will slide. Defaults to down.",
    )


class SlideDirection(Enum):
    UP = auto()
    DOWN = auto()


class ColumnSlide(base_effect.Effect):
    """Effect that slides each column into place."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        """Effect that slides each column into place.

        Args:
            input_data (str): string from stdin
            args (argparse.Namespace): arguments from argparse
        """
        super().__init__(terminal, args.animation_rate)
        self.column_delay_distance: int = 2  # number of characters to wait before adding a new row
        if args.slide_direction == "down":
            self.slide_direction = SlideDirection.DOWN
        else:
            self.slide_direction = SlideDirection.UP

    def prepare_data(self) -> None:
        """Prepares the data for the effect by grouping the characters by column and setting the starting
        coordinate."""

        self.columns = self.input_by_column()
        if self.slide_direction == SlideDirection.DOWN:
            for column_list in self.columns.values():
                column_list.reverse()
        for column in self.columns.values():
            for character in column:
                character.is_active = False
                if self.slide_direction == SlideDirection.DOWN:
                    character.current_coord.row = self.terminal.output_area.top
                else:
                    character.current_coord.row = self.terminal.output_area.bottom

    def get_next_column(self) -> list[base_character.EffectCharacter]:
        """Gets the next column of characters to animate.

        Returns:
            list[character.EffectCharacter]: The next column of characters to animate.
        """
        next_column = self.columns[min(self.columns.keys())]
        del self.columns[min(self.columns.keys())]
        return next_column

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        active_columns: list[list[base_character.EffectCharacter]] = []
        active_columns.append(self.get_next_column())
        column_delay_countdown = self.column_delay_distance
        self.terminal.print()
        while active_columns or self.animating_chars or self.columns:
            if column_delay_countdown == 0 and self.columns:
                active_columns.append(self.get_next_column())
                column_delay_countdown = self.column_delay_distance
            else:
                if self.columns:
                    column_delay_countdown -= 1
            for column in active_columns:
                if column:
                    next_character = column.pop(0)
                    next_character.is_active = True
                    self.animating_chars.append(next_character)
            self.animate_chars()

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.animation_completed()
            ]
            active_columns = [column for column in active_columns if column]
            self.terminal.print()
            time.sleep(self.animation_rate)

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            animating_char.move()
