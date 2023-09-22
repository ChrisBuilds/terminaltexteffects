import argparse
from enum import Enum, auto

from terminaltexteffects import base_character, base_effect
from terminaltexteffects.utils.terminal import Terminal
from terminaltexteffects.utils import argtypes


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "columnslide",
        formatter_class=argtypes.CustomFormatter,
        help="Slides each column into place from the outside to the middle.",
        description="columnslide | Slides each column into place from the outside to the middle.",
        epilog=f"""{argtypes.EASING_EPILOG}
            
Example: terminaltexteffects columnslide -a 0.003 --slide-direction up --easing IN_OUT_SINE --movement-speed 0.2 --column-gap 5""",
    )
    effect_parser.set_defaults(effect_class=ColumnSlide)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.003,
        help="Time to sleep, in seconds, between animation steps.",
    )
    effect_parser.add_argument(
        "--column-gap",
        default=5,
        type=argtypes.valid_gap,
        help="Number of characters to wait before adding a new column.",
    )
    effect_parser.add_argument(
        "--slide-direction",
        default="down",
        choices=["up", "down"],
        help="Direction the text will slide.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.valid_speed,
        default=0.2,
        metavar="(float > 0)",
        help="Character movement speed. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="IN_OUT_SINE",
        type=argtypes.valid_ease,
        help="Easing function to use for column movement.",
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
        super().__init__(terminal, args)
        self.column_gap: int = args.column_gap
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
                    character.motion.set_coordinate(character.input_coord.column, self.terminal.output_area.top)
                else:
                    character.motion.set_coordinate(character.input_coord.column, self.terminal.output_area.bottom)
                character.motion.new_waypoint(
                    "input_coord",
                    character.input_coord.column,
                    character.input_coord.row,
                    speed=self.args.movement_speed,
                    ease=self.args.easing,
                )
                character.motion.activate_waypoint("input_coord")

    def get_next_column(self) -> list[base_character.EffectCharacter]:
        """Gets the next column of characters to animate.

        Returns:
            list[character.EffectCharacter]: The next column of characters to animate.
        """
        if len(self.columns) % 2:
            next_column = self.columns.pop(max(self.columns.keys()))
        else:
            next_column = self.columns.pop(min(self.columns.keys()))
        return next_column

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        active_columns: list[list[base_character.EffectCharacter]] = []
        active_columns.append(self.get_next_column())
        column_delay_countdown = self.column_gap
        self.terminal.print()
        while active_columns or self.animating_chars or self.columns:
            if (column_delay_countdown == 0 and self.columns) or (self.columns and not active_columns):
                active_columns.append(self.get_next_column())
                column_delay_countdown = self.column_gap
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
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.motion.movement_complete()
            ]
            active_columns = [column for column in active_columns if column]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the tween method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
