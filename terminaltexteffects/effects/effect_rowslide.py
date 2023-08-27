import argparse
from enum import Enum, auto

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_character, base_effect
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "rowslide",
        help="Slides each row into place.",
        description="rowslide | Slides each row into place.",
        epilog="Example: terminaltexteffects rowslide -a 0.003 --slide-direction left",
    )
    effect_parser.set_defaults(effect_class=RowSlide)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=float,
        default=0.01,
        help="Time between animation steps. Defaults to 0.01 seconds.",
    )
    effect_parser.add_argument(
        "--slide-direction",
        default="left",
        choices=["left", "right"],
        help="Direction the text will slide. Defaults to left.",
    )


class SlideDirection(Enum):
    LEFT = auto()
    RIGHT = auto()


class RowSlide(base_effect.Effect):
    """Effect that slides each row into place."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        """Effect that slides each row into place.

        Args:
            terminal (Terminal): terminal to use for the effect
            args (argparse.Namespace): arguments from argparse
        """
        super().__init__(terminal)
        self.row_delay_distance: int = 8  # number of characters to wait before adding a new row
        if args.slide_direction == "left":
            self.slide_direction = SlideDirection.LEFT
        else:
            self.slide_direction = SlideDirection.RIGHT

    def prepare_data(self) -> None:
        """Prepares the data for the effect by grouping the characters by row and setting the starting
        coordinate."""

        self.rows = self.input_by_row()
        for row in self.rows.values():
            for character in row:
                character.is_active = False
                if self.slide_direction == SlideDirection.LEFT:
                    character.current_coord.column = self.terminal.output_area.right
                else:
                    character.current_coord.column = 0

    def get_next_row(self) -> list[base_character.EffectCharacter]:
        """Gets the next row of characters to animate.

        Returns:
            list[effect_char.EffectCharacter]: The next row of characters to animate.
        """
        next_row = self.rows[min(self.rows.keys())]
        del self.rows[min(self.rows.keys())]
        return next_row

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        active_rows: list[list[base_character.EffectCharacter]] = []
        active_rows.append(self.get_next_row())
        row_delay_countdown = self.row_delay_distance
        while active_rows or self.animating_chars:
            if row_delay_countdown == 0 and self.rows:
                active_rows.append(self.get_next_row())
                row_delay_countdown = self.row_delay_distance
            else:
                if self.rows:
                    row_delay_countdown -= 1
            for row in active_rows:
                if row:
                    if self.slide_direction == SlideDirection.LEFT:
                        next_character = row.pop(0)
                        next_character.is_active = True
                        self.animating_chars.append(next_character)
                    else:
                        next_character = row.pop(-1)
                        next_character.is_active = True
                        self.animating_chars.append(next_character)
            self.animate_chars()
            self.terminal.print()
            self.animating_chars = [
                animating_char for animating_char in self.animating_chars if not animating_char.is_movement_complete()
            ]
            active_rows = [row for row in active_rows if row]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method."""
        for animating_char in self.animating_chars:
            animating_char.move()
