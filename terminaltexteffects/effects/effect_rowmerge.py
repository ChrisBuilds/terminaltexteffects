import argparse

import terminaltexteffects.utils.argtypes as argtypes
from terminaltexteffects import base_effect
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "rowmerge",
        formatter_class=argtypes.CustomFormatter,
        help="Merges rows of characters.",
        description="rowmerge | Merges rows of characters.",
        epilog=f"""{argtypes.EASING_EPILOG}        
        
Example: terminaltexteffects rowmerge -a 0.01""",
    )
    effect_parser.set_defaults(effect_class=RowMergeEffect)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.01,
        help="Time, in seconds, to sleep between animation steps.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.valid_speed,
        default=0.5,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="OUT_QUAD",
        type=argtypes.valid_ease,
        help="Easing function to use for row movement.",
    )


class RowMergeEffect(base_effect.Effect):
    """Effect that merges rows."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        super().__init__(terminal, args)

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting every other row to start at the opposite
        side of the terminal and reverse the order."""

        self.rows = []
        for row_index, row in self.input_by_row().items():
            if row_index % 2 == 0:
                row = row[::-1]
                column = self.terminal.output_area.left
            else:
                column = self.terminal.output_area.right
            for character in row:
                character.is_active = False
                character.motion.set_coordinate(column, character.input_coord.row)
                character.motion.new_waypoint(
                    "input_coord",
                    character.input_coord.column,
                    character.input_coord.row,
                    speed=self.args.movement_speed,
                    ease=self.args.easing,
                )
                character.motion.activate_waypoint("input_coord")
            self.rows.append(row)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.rows or self.animating_chars:
            self.animate_chars()
            for row in self.rows:
                if row:
                    next_character = row.pop(0)
                    next_character.is_active = True
                    self.animating_chars.append(next_character)
            self.rows = [row for row in self.rows if row]

            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.motion.movement_complete()
            ]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
