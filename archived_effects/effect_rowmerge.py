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
        type=argtypes.nonnegative_float,
        default=0.01,
        help="Time, in seconds, to sleep between animation steps.",
    )
    effect_parser.add_argument(
        "--movement-speed",
        type=argtypes.positive_float,
        default=0.5,
        metavar="(float > 0)",
        help="Movement speed of the characters. Note: Speed effects the number of steps in the easing function. Adjust speed and animation rate separately to fine tune the effect.",
    )
    effect_parser.add_argument(
        "--easing",
        default="OUT_QUAD",
        type=argtypes.ease,
        help="Easing function to use for row movement.",
    )


class RowMergeEffect:
    """Effect that merges rows."""

    def __init__(self, terminal: Terminal, args: argparse.Namespace):
        self.terminal = terminal
        self.args = args
        self.pending_chars: list[EffectCharacter] = []
        self.active_chars: list[EffectCharacter] = []
        self.rows: list[list[EffectCharacter]] = []

    def prepare_data(self) -> None:
        """Prepares the data for the effect by setting every other row to start at the opposite
        side of the terminal and reverse the order."""

        for row_index, row in enumerate(
            self.terminal.get_characters_sorted(sort_order=self.terminal.CharacterSort.ROW_BOTTOM_TO_TOP)
        ):
            if row_index % 2 == 0:
                row = row[::-1]
                column = self.terminal.output_area.left
            else:
                column = self.terminal.output_area.right
            for character in row:
                self.terminal.set_character_visibility(character, False)
                character.motion.set_coordinate(motion.Coord(column, character.input_coord.row))

                input_coord_path = character.motion.new_path(speed=self.args.movement_speed, ease=self.args.easing)
                input_coord_path.new_waypoint(character.input_coord)
                character.motion.activate_path(input_coord_path)
            self.rows.append(row)

    def run(self) -> None:
        """Runs the effect."""
        self.prepare_data()
        while self.rows or self.active_chars:
            self.animate_chars()
            for row in self.rows:
                if row:
                    next_character = row.pop(0)
                    next_character.is_visible = True
                    self.active_chars.append(next_character)
            self.rows = [row for row in self.rows if row]

            self.active_chars = [character for character in self.active_chars if character.is_active]
            self.terminal.print()

    def animate_chars(self) -> None:
        """Animates the characters by calling the move method and printing the characters to the terminal."""
        for character in self.active_chars:
            character.motion.move()
