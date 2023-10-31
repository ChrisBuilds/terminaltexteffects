import argparse

from terminaltexteffects.utils import argtypes, motion
from terminaltexteffects.base_character import EffectCharacter
from terminaltexteffects.utils.terminal import Terminal


def add_arguments(subparsers: argparse._SubParsersAction) -> None:
    """Adds arguments to the subparser.

    Args:
        subparser (argparse._SubParsersAction): subparser to add arguments to
    """
    effect_parser = subparsers.add_parser(
        "verticalslice",
        formatter_class=argtypes.CustomFormatter,
        help="Slices the input in half vertically and slides it into place from opposite directions.",
        description="verticalslice | Slices the input in half vertically and slides it into place from opposite directions.",
        epilog=f"""{argtypes.EASING_EPILOG}
        
Example: terminaltexteffects verticalslice -a 0.02""",
    )
    effect_parser.set_defaults(effect_class=VerticalSlice)
    effect_parser.add_argument(
        "-a",
        "--animation-rate",
        type=argtypes.valid_animationrate,
        default=0.02,
        help="Time, in seconds, between animation steps.",
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
        default="IN_OUT_EXPO",
        type=argtypes.valid_ease,
        help="Easing function to use for character movement.",
    )


class VerticalSlice:
    """Effect that slices the input in half vertically and slides it into place from opposite directions."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.animating_chars: list[EffectCharacter] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting the left half to start at the top and the
        right half to start at the bottom, and creating rows consisting off halves from opposite
        input rows."""

        self.rows = list(self.terminal.input_by_row().values())
        lengths = [max([c.input_coord.column for c in row]) for row in self.rows]
        mid_point = sum(lengths) // len(lengths) // 2
        self.new_rows = []
        for row_index, row in enumerate(self.rows):
            new_row = []
            left_half = [character for character in row if character.input_coord.column <= mid_point]
            for character in left_half:
                character.motion.set_coordinate(
                    motion.Coord(character.input_coord.column, self.terminal.output_area.top)
                )
                input_coord_wpt = character.motion.new_waypoint(
                    "input_coord",
                    character.input_coord,
                    speed=self.args.movement_speed,
                    ease=self.args.easing,
                )
                character.motion.activate_waypoint(input_coord_wpt)
            opposite_row = self.rows[-(row_index + 1)]
            right_half = [c for c in opposite_row if c.input_coord.column > mid_point]
            for character in right_half:
                character.motion.set_coordinate(
                    motion.Coord(character.input_coord.column, self.terminal.output_area.bottom)
                )
                input_coord_wpt = character.motion.new_waypoint(
                    "input_coord",
                    character.input_coord,
                    speed=self.args.movement_speed,
                    ease=self.args.easing,
                )
                character.motion.activate_waypoint(input_coord_wpt)
            new_row.extend(left_half)
            new_row.extend(right_half)
            self.new_rows.append(new_row)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.new_rows or self.animating_chars:
            if self.new_rows:
                next_row = self.new_rows.pop(0)
                for character in next_row:
                    character.is_active = True
                self.animating_chars.extend(next_row)
            self.animate_chars()
            self.terminal.print()
            # remove completed chars from animating chars
            self.animating_chars = [
                animating_char
                for animating_char in self.animating_chars
                if not animating_char.motion.movement_is_complete()
            ]

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and printing the characters to the terminal."""
        for animating_char in self.animating_chars:
            animating_char.motion.move()
